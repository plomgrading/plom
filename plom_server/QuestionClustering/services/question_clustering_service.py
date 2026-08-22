# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2026 Colin B. Macdonald
# Copyright (C) 2026 Deep Shah

from collections import defaultdict
from importlib import resources
import os
from pathlib import Path
import re
from typing import Any, Mapping, Optional

import numpy as np
import yaml

# django
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.db import transaction
from django_huey import db_task
import huey
import huey.api
from django.db.models import Count, Max
from django.db.models import QuerySet

# plom db models
from plom_server.Base.models import User
from plom_server.Mark.models import MarkingTask, MarkingTaskTag
from plom_server.QuestionClustering.models import (
    QuestionClusteringChore,
    QVClusterLink,
    QVCluster,
    ClusteringGroupType,
)
from plom_server.Papers.models import Paper
from plom_server.Base.models import HueyTaskTracker
from plom_server.QuestionClustering.models import ClusteringModelType

# plom_server services
from plom_server.Mark.services.marking_task_service import MarkingTaskService
from plom_server.Mark.services import MarkingPriorityService
from plom_server.Papers.services import PaperInfoService
from plom_server.Rectangles.services import (
    RectangleExtractor,
)
from plom_server.QuestionClustering.services.model_loader import get_ClusteringStrategy
from plom_server.QuestionClustering.services.mcq_checkbox_ml import (
    MCQCheckboxCrop,
    MCQCheckboxMLClient,
    MCQCheckboxMLServiceError,
)

# exception
from plom_server.QuestionClustering.exceptions.clustering_exception import (
    EmptySelectedError,
)

# plom_ml
import plom_ml.clustering.model
from plom_ml.clustering.pipeline.clustering_pipeline import ClusteringPipeline
from plom_ml.clustering.preprocessing.image_processing_service import (
    ImageProcessingService,
)
from plom_ml.clustering.preprocessing.preprocessor import DiffProcessor

MCQ_BLANK_CLUSTER_ID_OFFSET = 0
MCQ_MULTIPLE_CLUSTER_ID_OFFSET = 1
MCQ_AMBIGUOUS_CLUSTER_ID_OFFSET = 2


class QuestionClusteringJobService:
    """Manage CRUDs of clustering jobs."""

    def start_cluster_qv_job(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
        clustering_model: ClusteringModelType,
        mcq_metadata: dict[str, Any] | None = None,
    ):
        """Run a background job to cluster papers for the given question region.

        question_idx: The question index used for clustering
        version: The question version used for clustering
        page_num: The page number used for clustering. NOTE: this is needed as there can be
            multi-pages question
        rect: the coordinates of the four corners of the rectangle used for clustering.
            rect should have these keys: [top, left, bottom, right].
        clustering_model: the model used to cluster the papers.
        mcq_metadata: optional MCQ checkbox template metadata.  This stores the
            per-option box coordinates, not cropped checkbox images.

        """
        expected_keys = {"top", "left", "bottom", "right"}
        if expected_keys.intersection(set(rect.keys())) != expected_keys:
            raise ValueError(
                f"rect must have these keys: {expected_keys}, but received: {rect.keys()}"
            )

        with transaction.atomic(durable=True):
            is_mcq_model = clustering_model == ClusteringModelType.MCQ
            x = QuestionClusteringChore.objects.create(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                top=rect["top"],
                left=rect["left"],
                bottom=rect["bottom"],
                right=rect["right"],
                clustering_model=clustering_model,
                mcq_metadata=mcq_metadata if is_mcq_model else {},
                status=HueyTaskTracker.STARTING,
            )
            tracker_pk = x.pk

        res = huey_cluster_single_qv(
            question_idx=question_idx,
            version=version,
            page_num=page_num,
            rect=rect,
            tracker_pk=tracker_pk,
            clustering_model=clustering_model,
            _debug_be_flaky=False,
        )
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    @transaction.atomic
    def get_clustering_job(self, task_id: int) -> dict[str, Any]:
        """Get clustering job representation in dict.

        Args:
            task_id: the clustering job id.

        Returns:
            A dict with these keys: [status, message, last_update, obsolete].
        """
        job = QuestionClusteringChore.objects.get(id=task_id)
        return model_to_dict(
            job, fields=["status", "message", "last_update", "obsolete"]
        )

    @transaction.atomic
    def delete_clustering_job(self, task_id: int) -> None:
        """Remove a clustering job and its owned clusters.

        Args:
            task_id: the id of the clustering task to be removed.

        Raises:
            ObjectDoesNOTExist: If the task does not exist.
        """
        QuestionClusteringChore.objects.get(id=task_id).delete()


class QuestionClusteringService:
    """Service handling clustering and querying of cluster-related models."""

    CLUSTER_NAME_MAX_LENGTH = 100  # must not exceed DB model field size
    _CLUSTER_TAG_RE = re.compile(r"^cluster_job\d+_(\d+)(?:_.*)?$")
    _INVALID_CLUSTER_TAG_NAME_CHARS_RE = re.compile(r"[^\w\-\+\:\;\.\@]+")

    def _store_clustered_result(
        self,
        paper_to_clusterId: dict[int, int],
        job: QuestionClusteringChore,
        question_idx: int,
        version: int,
        page_num: int,
        rect,
    ) -> None:
        """Store clustering result to database.

        Args:
            paper_to_clusterId: a mapping from paper_number to clusterId.
            job: clustering job that owns these clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page used in the clustering.
            rect: the rectangular region used in the clustering.
        """
        # get id to paper_nums mapping
        clusterId_to_papers = defaultdict(set)
        for pn, clusterId in paper_to_clusterId.items():
            clusterId_to_papers[clusterId].add(pn)

        with transaction.atomic():
            for clusterId, paper_nums in clusterId_to_papers.items():
                # create user facing grouping
                user_facing_cluster = QVCluster.objects.create(
                    question_idx=question_idx,
                    version=version,
                    job=job,
                    clusterId=clusterId,
                    type=ClusteringGroupType.user_facing,
                    page_num=page_num,
                    top=rect["top"],
                    left=rect["left"],
                    bottom=rect["bottom"],
                    right=rect["right"],
                )

                base_cluster = QVCluster.objects.create(
                    question_idx=question_idx,
                    version=version,
                    job=job,
                    clusterId=clusterId,
                    type=ClusteringGroupType.original,
                    page_num=page_num,
                    top=rect["top"],
                    left=rect["left"],
                    bottom=rect["bottom"],
                    right=rect["right"],
                    user_cluster=user_facing_cluster,
                )

                # Use .filter instead of .get in for loop to avoid n+1 queries
                papers = Paper.objects.filter(paper_number__in=paper_nums)
                base_cluster.paper.add(*papers)
                user_facing_cluster.paper.add(*papers)

    def _get_mcq_option_boxes(
        self, mcq_metadata: dict[str, Any] | None
    ) -> list[dict[str, float | str]]:
        """Return normalized MCQ option boxes from stored metadata."""
        if not isinstance(mcq_metadata, dict):
            return []
        boxes = mcq_metadata.get("boxes", [])
        if not isinstance(boxes, list):
            return []

        normalized_boxes: list[dict[str, float | str]] = []
        for box in boxes:
            if not isinstance(box, dict):
                continue
            try:
                normalized_boxes.append(
                    {
                        "label": str(box["label"]),
                        "left": float(box["left"]),
                        "top": float(box["top"]),
                        "right": float(box["right"]),
                        "bottom": float(box["bottom"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        return normalized_boxes

    def _get_mcq_mark_score(self, ref: np.ndarray, scanned: np.ndarray) -> float:
        """Score how much extra student marking appears in one option box."""
        diff = ImageProcessingService().get_diff(ref, scanned, dilation_iteration=1)
        if diff.size == 0:
            return 0.0
        return float(np.count_nonzero(diff)) / float(diff.size)

    def _get_mcq_mark_threshold(self, scores: list[float]) -> float:
        """Pick an adaptive threshold for checkbox mark scores."""
        if not scores:
            return 0.01

        score_array = np.array(scores)
        median = float(np.median(score_array))
        mad = float(np.median(np.abs(score_array - median)))
        return max(0.01, median + 6 * mad)

    def _classify_mcq_papers_by_option_boxes(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        paper_numbers: list[int],
        option_boxes: list[dict[str, float | str]],
    ) -> dict[int, int]:
        """Classify each paper by which stored MCQ option box is marked."""
        rex = RectangleExtractor(version, page_num)
        labels = [str(box["label"]) for box in option_boxes]
        label_to_cluster_id = {label: idx for idx, label in enumerate(labels)}
        blank_cluster_id = len(labels) + MCQ_BLANK_CLUSTER_ID_OFFSET
        multiple_cluster_id = len(labels) + MCQ_MULTIPLE_CLUSTER_ID_OFFSET
        ambiguous_cluster_id = len(labels) + MCQ_AMBIGUOUS_CLUSTER_ID_OFFSET

        box_rect_by_label = {
            str(box["label"]): {
                "left": float(box["left"]),
                "top": float(box["top"]),
                "right": float(box["right"]),
                "bottom": float(box["bottom"]),
            }
            for box in option_boxes
        }
        ref_by_label = {
            label: rex.get_cropped_ref_img(box_rect)
            for label, box_rect in box_rect_by_label.items()
        }
        paper_to_scores: dict[int, dict[str, float]] = {}
        paper_to_cluster_id: dict[int, int] = {}
        all_scores: list[float] = []

        for paper_number in paper_numbers:
            option_scores: dict[str, float] = {}
            for label, box_rect in box_rect_by_label.items():
                scanned = rex.get_cropped_scanned_img_or_none(paper_number, box_rect)
                if scanned is None:
                    option_scores = {}
                    break

                score = self._get_mcq_mark_score(ref_by_label[label], scanned)
                option_scores[label] = score
                all_scores.append(score)

            if option_scores:
                paper_to_scores[paper_number] = option_scores
            else:
                paper_to_cluster_id[paper_number] = ambiguous_cluster_id

        threshold = self._get_mcq_mark_threshold(all_scores)
        for paper_number, option_scores in paper_to_scores.items():
            max_score = max(option_scores.values())
            if max_score < threshold:
                paper_to_cluster_id[paper_number] = blank_cluster_id
                continue

            selected_threshold = max(threshold, max_score * 0.45)
            selected_labels = [
                label
                for label, score in option_scores.items()
                if score >= selected_threshold
            ]

            if len(selected_labels) == 1:
                paper_to_cluster_id[paper_number] = label_to_cluster_id[
                    selected_labels[0]
                ]
            elif len(selected_labels) > 1:
                paper_to_cluster_id[paper_number] = multiple_cluster_id
            else:
                paper_to_cluster_id[paper_number] = ambiguous_cluster_id

        return paper_to_cluster_id

    def _classify_mcq_papers_by_ml_option_boxes(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        paper_numbers: list[int],
        option_boxes: list[dict[str, float | str]],
    ) -> dict[int, int]:
        """Classify MCQ papers by sending corrected option-box crops to ML service."""
        rex = RectangleExtractor(version, page_num)
        labels = [str(box["label"]) for box in option_boxes]
        label_to_cluster_id = {label: idx for idx, label in enumerate(labels)}
        blank_cluster_id = len(labels) + MCQ_BLANK_CLUSTER_ID_OFFSET
        multiple_cluster_id = len(labels) + MCQ_MULTIPLE_CLUSTER_ID_OFFSET
        ambiguous_cluster_id = len(labels) + MCQ_AMBIGUOUS_CLUSTER_ID_OFFSET

        box_rect_by_label = {
            str(box["label"]): {
                "left": float(box["left"]),
                "top": float(box["top"]),
                "right": float(box["right"]),
                "bottom": float(box["bottom"]),
            }
            for box in option_boxes
        }

        paper_to_cluster_id: dict[int, int] = {}
        crops: list[MCQCheckboxCrop] = []
        for paper_number in paper_numbers:
            paper_crops: list[MCQCheckboxCrop] = []
            for label, box_rect in box_rect_by_label.items():
                scanned = rex.get_cropped_scanned_img_or_none(paper_number, box_rect)
                if scanned is None:
                    paper_crops = []
                    break
                paper_crops.append(
                    MCQCheckboxCrop(
                        box_id=f"mcq-{len(crops) + len(paper_crops)}",
                        label=label,
                        image=scanned,
                        paper_number=paper_number,
                    )
                )

            if paper_crops:
                crops.extend(paper_crops)
            else:
                paper_to_cluster_id[paper_number] = ambiguous_cluster_id

        predictions = MCQCheckboxMLClient(
            settings.PLOM_ML_SERVICE_URL,
            token=settings.PLOM_ML_SERVICE_TOKEN,
            timeout=settings.PLOM_ML_SERVICE_TIMEOUT,
            batch_size=settings.PLOM_ML_SERVICE_MCQ_BATCH_SIZE,
        ).predict(crops)
        predictions_by_paper: dict[int, list] = defaultdict(list)
        for prediction in predictions:
            if prediction.paper_number is None:
                continue
            predictions_by_paper[prediction.paper_number].append(prediction)

        for paper_number in paper_numbers:
            if paper_number in paper_to_cluster_id:
                continue

            paper_predictions = predictions_by_paper.get(paper_number, [])
            prediction_by_label = {
                prediction.label: prediction for prediction in paper_predictions
            }
            if set(prediction_by_label) != set(labels):
                paper_to_cluster_id[paper_number] = ambiguous_cluster_id
                continue

            selected_labels = [
                label for label in labels if prediction_by_label[label].marked
            ]
            if len(selected_labels) == 0:
                suspicious_fill_ratio = (
                    settings.PLOM_ML_SERVICE_MCQ_SUSPICIOUS_FILL_RATIO
                )
                suspicious_labels = [
                    label
                    for label in labels
                    if prediction_by_label[label].uncertain
                    and prediction_by_label[label].fill_ratio >= suspicious_fill_ratio
                ]
                if len(suspicious_labels) == 1:
                    paper_to_cluster_id[paper_number] = label_to_cluster_id[
                        suspicious_labels[0]
                    ]
                elif len(suspicious_labels) > 1:
                    paper_to_cluster_id[paper_number] = ambiguous_cluster_id
                else:
                    paper_to_cluster_id[paper_number] = blank_cluster_id
            elif len(selected_labels) == 1:
                paper_to_cluster_id[paper_number] = label_to_cluster_id[
                    selected_labels[0]
                ]
            else:
                paper_to_cluster_id[paper_number] = multiple_cluster_id

        return paper_to_cluster_id

    def cluster_mcq(
        self,
        job: QuestionClusteringChore,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
        mcq_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Cluster mcq responses within the given rect for (q, v) context.

        Args:
            job: clustering job that owns the created clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page_number used for the clustering.
            rect: the rectangular region used for clustering.
            mcq_metadata: optional per-option checkbox metadata.

        Raises:
            ValueError: problem extracting from reference image.
        """
        option_boxes = self._get_mcq_option_boxes(mcq_metadata)
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )
        if option_boxes:
            if settings.PLOM_ML_SERVICE_URL:
                try:
                    paper_to_clusterId = self._classify_mcq_papers_by_ml_option_boxes(
                        question_idx, version, page_num, paper_numbers, option_boxes
                    )
                except MCQCheckboxMLServiceError as err:
                    raise ValueError(f"MCQ checkbox ML service failed: {err}") from err
            else:
                paper_to_clusterId = self._classify_mcq_papers_by_option_boxes(
                    question_idx, version, page_num, paper_numbers, option_boxes
                )
            if not paper_to_clusterId:
                raise ValueError("Could not classify ANY MCQ papers")

            self._store_clustered_result(
                paper_to_clusterId, job, question_idx, version, page_num, rect
            )
            return

        # Jobs created before checkbox metadata was added continue to use the
        # legacy region-level MCQ clustering model.
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rect)

        # get paper_num to ref, scanned mapping used for clustering input
        # the key names (ref, scanned) are known from the type of Preprocessor (DiffProcessor)
        paper_to_images: Mapping[int, Mapping[str, Any]] = {
            pn: {"ref": ref, "scanned": rex.get_cropped_scanned_img_or_none(pn, rect)}
            for pn in paper_numbers
        }
        # filter out any that failed
        paper_to_images = {
            pn: x for pn, x in paper_to_images.items() if x["scanned"] is not None
        }
        if not paper_to_images:
            raise ValueError("Could not extract rectangles from ANY pages")

        # get mcq ClusteringStrategy (use @lru_cache)
        ClusteringStrategy = get_ClusteringStrategy(model_type=ClusteringModelType.MCQ)

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            ClusteringStrategy=ClusteringStrategy,
            preprocessor=DiffProcessor(dilation_strength=1, invert=False),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, job, question_idx, version, page_num, rect
        )

    def cluster_hme(
        self,
        job: QuestionClusteringChore,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
    ) -> None:
        """Cluster handwritten math expression responses within the given rect for (q, v) context.

        Args:
            job: clustering job that owns the created clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page_number used for the clustering.
            rect: the rectangular region used for clustering.

        Raises:
            ValueError: extraction from problem reference image.
        """
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rect)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # get paper_num to ref, scanned mapping used for clustering input
        # the key names (ref, scanned) are known from the type of Preprocessor (DiffProcessor)
        # TODO: why do we need typing here?
        paper_to_images: Mapping[int, Mapping[str, Any]] = {
            pn: {"ref": ref, "scanned": rex.get_cropped_scanned_img_or_none(pn, rect)}
            for pn in paper_numbers
        }
        # filter out any that failed
        paper_to_images = {
            pn: x for pn, x in paper_to_images.items() if x["scanned"] is not None
        }
        if not paper_to_images:
            raise ValueError("Could not extract rectangles from ANY pages")

        # load model
        ClusteringStrategy = get_ClusteringStrategy(model_type=ClusteringModelType.HME)

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            ClusteringStrategy=ClusteringStrategy,
            preprocessor=DiffProcessor(dilation_strength=1, invert=True),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, job, question_idx, version, page_num, rect
        )

    def cluster_qv(
        self,
        job: QuestionClusteringChore,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
        clustering_model: ClusteringModelType,
        mcq_metadata: dict[str, Any] | None = None,
    ):
        """Run clustering on a (q, v) in the given rect with the specified clustering model.

        Args:
            job: clustering job that owns the created clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page num involved in the clustering.
            rect: the rectangular region used for clustering.
            clustering_model: the model used for clustering.
            mcq_metadata: optional stored MCQ option-box metadata.

        Raises:
            ValueError: extraction from problem reference image.
        """
        if clustering_model == ClusteringModelType.MCQ:
            self.cluster_mcq(job, question_idx, version, page_num, rect, mcq_metadata)

        elif clustering_model == ClusteringModelType.HME:
            self.cluster_hme(job, question_idx, version, page_num, rect)

    def get_question_clustering_tasks(self) -> list[dict]:
        """Get all non-obsolete clustering tasks.

        Returns:
            A list of dicts each representing a non-obsolete clustering task. The dict
            has these keys: [task_id, question_idx, version, page_num, status, message].
        """
        return [
            {
                "task_id": task.id,
                "question_idx": task.question_idx,
                "version": task.version,
                "page_num": task.page_num,
                "status": task.get_status_display(),
                "message": task.message,
            }
            for task in QuestionClusteringChore.objects.filter(obsolete=False)
        ]

    def get_clustering_chore(self, task_id: int) -> QuestionClusteringChore:
        """Get a clustering job by id."""
        return QuestionClusteringChore.objects.get(id=task_id)

    def get_clusters_and_member_count(self, task_id: int) -> list[tuple]:
        """Get a list of (clusterId, member_count) for all clusters in a job.

        Args:
            task_id: clustering job id.

        Returns:
            A list of tuple of (clusterId, member_count) for all clsuters in a (q, v) context.
            The list is sorted by clusterId
        """
        qs = (
            QVCluster.objects.filter(
                job_id=task_id,
                type=ClusteringGroupType.user_facing,
            )
            .annotate(count=Count("paper"))
            .values("clusterId", "count")
            .order_by("clusterId")
        )

        return [(q["clusterId"], q["count"]) for q in qs]

    def get_paper_nums_in_clusters(self, task_id: int) -> dict[int, list[int]]:
        """Get a mapping from clusterId to the paper_num of papers under the given cluster.

        Args:
            task_id: clustering job id.

        Returns:
            A dict mapping clusterId to a list of paper_numbers for all clusters in a (q, v) context.
        """
        qs = QVCluster.objects.filter(
            job_id=task_id,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        result = {
            item.clusterId: [paper.paper_number for paper in item.paper.all()]
            for item in qs
        }

        return result

    def get_cluster_name_map(self, task_id: int) -> dict[int, str]:
        """Get a mapping from clusterId to human-readable cluster name."""
        return dict(
            QVCluster.objects.filter(
                job_id=task_id,
                type=ClusteringGroupType.user_facing,
            ).values_list("clusterId", "cluster_name")
        )

    def update_cluster_name(
        self, task_id: int, clusterId: int, cluster_name: str
    ) -> str:
        """Update the human-readable name of a user-facing cluster."""
        clean_name = cluster_name.strip()
        if len(clean_name) > self.CLUSTER_NAME_MAX_LENGTH:
            raise ValueError(
                f"Cluster name must be at most {self.CLUSTER_NAME_MAX_LENGTH} characters."
            )

        cluster = QVCluster.objects.get(
            job_id=task_id,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        cluster.cluster_name = clean_name
        cluster.save(update_fields=["cluster_name"])
        return clean_name

    def get_unclustered_paper_nums(self, task_id: int) -> list[int]:
        """Get scanned paper numbers that are not in any user-facing cluster.

        Args:
            task_id: clustering job id.

        Returns:
            A sorted list of scanned paper numbers for the page/version that are not
            currently linked to a user-facing cluster for the question/version.
        """
        job = self.get_clustering_chore(task_id)
        scanned_paper_nums = set(
            PaperInfoService.get_paper_numbers_containing_page(
                job.page_num, version=job.version, scanned=True
            )
        )
        clustered_paper_nums = set(
            QVCluster.objects.filter(
                job=job,
                type=ClusteringGroupType.user_facing,
            )
            .values_list("paper__paper_number", flat=True)
            .distinct()
        )

        return sorted(scanned_paper_nums - clustered_paper_nums)

    @transaction.atomic
    def assign_papers_to_cluster(
        self, task_id: int, clusterId: int, paper_nums: list[int]
    ) -> int:
        """Assign papers to a user-facing cluster.

        If any selected papers are already in another user-facing cluster for the
        same question/version, they are moved to the target cluster.

        Args:
            task_id: clustering job id.
            clusterId: the id of the target cluster.
            paper_nums: the paper numbers to assign to the target cluster.

        Raises:
            EmptySelectedError: if no paper numbers are provided.
            ObjectDoesNotExist: if the target cluster does not exist.

        Returns:
            The count of members in the target cluster after assignment.
        """
        if len(paper_nums) == 0:
            raise EmptySelectedError("attempting to assign 0 papers to cluster.")

        unique_paper_nums = set(paper_nums)
        target_cluster = QVCluster.objects.get(
            job_id=task_id,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        papers = Paper.objects.filter(paper_number__in=unique_paper_nums)

        clusters = QVCluster.objects.filter(
            job_id=task_id,
            type=ClusteringGroupType.user_facing,
        )
        QVClusterLink.objects.filter(
            qv_cluster__in=clusters,
            paper__paper_number__in=unique_paper_nums,
        ).delete()

        target_cluster.paper.add(*papers)

        return target_cluster.paper.count()

    @transaction.atomic
    def create_cluster_from_papers(
        self, task_id: int, paper_nums: list[int]
    ) -> tuple[int, int]:
        """Create a new user-facing cluster from selected papers.

        Args:
            task_id: clustering job id.
            paper_nums: paper numbers to put in the new cluster.

        Raises:
            EmptySelectedError: if no paper numbers are provided.

        Returns:
            A tuple of (new cluster id, member count).
        """
        if len(paper_nums) == 0:
            raise EmptySelectedError("attempting to create cluster from 0 papers.")

        job = self.get_clustering_chore(task_id)
        unique_paper_nums = set(paper_nums)
        next_cluster_id = (
            QVCluster.objects.filter(job=job)
            .aggregate(max_cluster_id=Max("clusterId"))
            .get("max_cluster_id")
        )
        next_cluster_id = 0 if next_cluster_id is None else next_cluster_id + 1

        rect = self.get_corners_used_for_clustering(task_id)
        new_cluster = QVCluster.objects.create(
            question_idx=job.question_idx,
            version=job.version,
            job=job,
            clusterId=next_cluster_id,
            type=ClusteringGroupType.user_facing,
            page_num=job.page_num,
            top=rect["top"],
            left=rect["left"],
            bottom=rect["bottom"],
            right=rect["right"],
        )
        papers = Paper.objects.filter(paper_number__in=unique_paper_nums)

        clusters = QVCluster.objects.filter(
            job=job,
            type=ClusteringGroupType.user_facing,
        ).exclude(pk=new_cluster.pk)
        QVClusterLink.objects.filter(
            qv_cluster__in=clusters,
            paper__paper_number__in=unique_paper_nums,
        ).delete()

        new_cluster.paper.add(*papers)

        return next_cluster_id, new_cluster.paper.count()

    def suggest_clusters_for_unclustered_papers(
        self, task_id: int
    ) -> list[dict[str, Any]]:
        """Suggest a target cluster for each currently unclustered paper.

        The suggestion uses the same model embeddings as the original
        clustering job, comparing each unclustered paper to the centroid
        embedding for each existing user-facing cluster. The output is advisory
        only; callers must still explicitly apply the suggested assignments.

        This method does not download model weights. If the relevant model is
        not already present in ``model_cache``, it raises ValueError so the UI
        can ask the user to run the clustering job/model setup first.

        Args:
            task_id: clustering job id.

        Returns:
            A list of suggestions sorted by paper number. Each suggestion has
            the keys: paper_num, clusterId, confidence, distance, and gap.
        """
        job = self.get_clustering_chore(task_id)
        unclustered_paper_nums = self.get_unclustered_paper_nums(task_id)
        if not unclustered_paper_nums:
            return []

        clustering_model = self.get_clustering_model_type(task_id)
        missing_weight_paths = self._missing_clustering_model_weight_paths(
            clustering_model
        )
        if missing_weight_paths:
            missing = ", ".join(str(path) for path in missing_weight_paths)
            raise ValueError(
                "Cannot suggest clusters because the clustering model weights "
                f"are not available locally: {missing}"
            )

        clusters = (
            QVCluster.objects.filter(
                job=job,
                type=ClusteringGroupType.user_facing,
            )
            .prefetch_related("paper")
            .order_by("clusterId")
        )
        if not clusters:
            return []

        rect = self.get_corners_used_for_clustering(task_id)
        rex = RectangleExtractor(job.version, job.page_num)
        ref = rex.get_cropped_ref_img(rect)
        preprocessor = DiffProcessor(
            dilation_strength=1,
            invert=clustering_model == ClusteringModelType.HME,
        )
        clustering_strategy = self._get_local_clustering_strategy(clustering_model)
        vector_cache: dict[int, np.ndarray | None] = {}

        def get_vector(paper_num: int) -> np.ndarray | None:
            if paper_num not in vector_cache:
                scanned = rex.get_cropped_scanned_img_or_none(paper_num, rect)
                if scanned is None:
                    vector_cache[paper_num] = None
                else:
                    processed = preprocessor.process({"ref": ref, "scanned": scanned})
                    vector_cache[paper_num] = clustering_strategy.get_embeddings(
                        processed
                    )
            return vector_cache[paper_num]

        cluster_centroids: list[tuple[int, np.ndarray]] = []
        for cluster in clusters:
            member_vectors = [
                vector
                for vector in (
                    get_vector(paper.paper_number) for paper in cluster.paper.all()
                )
                if vector is not None
            ]
            if member_vectors:
                cluster_centroids.append(
                    (cluster.clusterId, np.mean(member_vectors, axis=0))
                )

        if not cluster_centroids:
            return []

        suggestions = []
        for paper_num in unclustered_paper_nums:
            vector = get_vector(paper_num)
            if vector is None:
                continue

            distances = sorted(
                (
                    (
                        clusterId,
                        self._embedding_distance(vector, centroid, clustering_model),
                    )
                    for clusterId, centroid in cluster_centroids
                ),
                key=lambda item: item[1],
            )
            clusterId, distance = distances[0]
            next_distance = distances[1][1] if len(distances) > 1 else None
            gap = self._suggestion_distance_gap(distance, next_distance)
            suggestions.append(
                {
                    "paper_num": paper_num,
                    "clusterId": clusterId,
                    "confidence": self._suggestion_confidence(gap),
                    "distance": round(distance, 4),
                    "gap": round(gap, 4),
                }
            )

        return suggestions

    def get_clustering_model_type(self, task_id: int) -> ClusteringModelType:
        """Return the clustering model used for a clustering job."""
        return ClusteringModelType(self.get_clustering_chore(task_id).clustering_model)

    @staticmethod
    def _embedding_distance(
        vector: np.ndarray,
        centroid: np.ndarray,
        clustering_model: ClusteringModelType,
    ) -> float:
        """Distance metric matching the original clustering strategy."""
        if clustering_model == ClusteringModelType.MCQ:
            denominator = np.linalg.norm(vector) * np.linalg.norm(centroid)
            if denominator == 0:
                return 1.0
            cosine_similarity = float(np.dot(vector, centroid) / denominator)
            return 1.0 - cosine_similarity
        return float(np.linalg.norm(vector - centroid))

    @staticmethod
    def _missing_clustering_model_weight_paths(
        clustering_model: ClusteringModelType,
    ) -> list[Path]:
        """Return model weight paths that are required but not available locally."""
        config_path = resources.files(plom_ml.clustering.model) / "model_config.yaml"
        with config_path.open("r") as f:
            config = yaml.safe_load(f)

        if clustering_model == ClusteringModelType.MCQ:
            filenames = [config["models"]["mcq"]["filename"]]
        elif clustering_model == ClusteringModelType.HME:
            filenames = [
                config["models"]["hme_symbolic"]["filename"],
                config["models"]["hme_trocr"]["filename"],
            ]
        else:
            raise ValueError(f"Unsupported clustering model: {clustering_model}")

        paths = [Path("model_cache") / filename for filename in filenames]
        return [path for path in paths if not path.exists()]

    @staticmethod
    def _get_local_clustering_strategy(clustering_model: ClusteringModelType):
        """Load a clustering strategy without allowing Hugging Face downloads."""
        previous_offline_value = os.environ.get("TRANSFORMERS_OFFLINE")
        previous_hf_offline_value = os.environ.get("HF_HUB_OFFLINE")
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            return get_ClusteringStrategy(clustering_model)
        except Exception as err:
            raise ValueError(
                "Cannot suggest clusters because the clustering model assets "
                "are not available locally."
            ) from err
        finally:
            if previous_offline_value is None:
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
            else:
                os.environ["TRANSFORMERS_OFFLINE"] = previous_offline_value
            if previous_hf_offline_value is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = previous_hf_offline_value

    @staticmethod
    def _suggestion_distance_gap(
        nearest_distance: float, next_distance: float | None
    ) -> float:
        """Return the relative gap between the best and runner-up match."""
        if next_distance is None or next_distance == 0:
            return 0.0
        return max((next_distance - nearest_distance) / next_distance, 0.0)

    @staticmethod
    def _suggestion_confidence(gap: float) -> str:
        """Map distance separation to a human-readable confidence level."""
        if gap >= 0.35:
            return "high"
        if gap >= 0.15:
            return "medium"
        return "low"

    def get_cluster_priority(self, task_id: int, clusterId: int) -> Optional[float]:
        """Get the priority value of a cluster in a (q, v) context.

        NOTE: If there exists some tasks with different priority values then the priority is None.

        Args:
            task_id: clustering job id.
            clusterId: the id of the cluster in query.

        Returns:
            Priority value of all the tasks in the cluster. If there exists some tasks with different
            priority values then returns None.
        """
        job = self.get_clustering_chore(task_id)
        papers = QVCluster.objects.get(
            job=job,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        ).paper.all()

        all_tasks = MarkingPriorityService.get_tasks_to_update_priority_by_q_v(
            job.question_idx, job.version
        )

        unique_priorities = (
            all_tasks.filter(paper__in=papers)
            .values_list("marking_priority", flat=True)
            .distinct()
        )

        if unique_priorities.count() == 1:
            return unique_priorities.first()
        else:
            return None

    def get_cluster_priority_map(self, task_id: int) -> dict[int, Optional[float]]:
        """Get the mapping of cluster id to priority value.

        NOTE: If there exists tasks under same cluster with conflicting priorities, the priority
            is set to None

        Args:
            task_id: clustering job id.

        Returns:
            A dict mapping clusterId to the priority val. Priority val is None if there are task
            priorities under the same cluster
        """
        return {
            cluster.clusterId: self.get_cluster_priority(task_id, cluster.clusterId)
            for cluster in QVCluster.objects.filter(
                job_id=task_id,
                type=ClusteringGroupType.user_facing,
            )
        }

    def update_priority_based_on_cluster_order(
        self, cluster_order: list[int], task_id: int
    ) -> None:
        """Update priority values based on the cluster table's order.

        NOTE: the priority values is given in the range of [0, len(cluster_order)],
            priority 0 is given to the papers that are not part of any clusters

        Args:
            cluster_order: an ordered list of clusterIds where lower index has higher priority.
            task_id: clustering job id.
        """
        job = self.get_clustering_chore(task_id)
        clusters = QVCluster.objects.filter(
            job=job,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        # grab all tasks
        tasks = MarkingPriorityService.get_tasks_to_update_priority_by_q_v(
            job.question_idx, job.version
        )

        paper_nums_in_clusters: set[int] = set()

        for i, clusterId in enumerate(cluster_order):
            # get the relevant tasks for every cluster
            curr_cluster = clusters.get(clusterId=clusterId)
            curr_papers = curr_cluster.paper.all()
            curr_tasks = tasks.filter(paper__in=curr_papers)

            # update all tasks under that cluster to the same priority val
            priority = len(cluster_order) - i
            # TODO: this is probably inefficient for large numbers of tasks
            # investigate using a bulk priority setter
            for task in curr_tasks:
                MarkingPriorityService.modify_task_priority(task, priority)

            paper_nums_in_clusters.update(p.paper_number for p in curr_papers)

        # update priority for paper not part of any cluster to 0
        task_not_in_cluster = tasks.exclude(
            paper__paper_number__in=paper_nums_in_clusters
        )
        for task in task_not_in_cluster:
            MarkingPriorityService.modify_task_priority(task, 0)

    def get_clusterid_to_paper_mapping(self, task_id: int) -> dict[int, list[Paper]]:
        """Get a dict mapping clusterId to list of papers under a q,v contenxt.

        Args:
            task_id: clustering job id.

        """
        clusters = QVCluster.objects.filter(
            job_id=task_id,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        return {cluster.clusterId: list(cluster.paper.all()) for cluster in clusters}

    @transaction.atomic
    def bulk_tagging(self, task_id: int, *, userid: int) -> None:
        """Bulk tag all clusters with default cluster tag.

        NOTE: current default cluster tag is cluster_job{task_id}_{clusterId},
        optionally followed by _{cluster_name} when a cluster has a name.

        Args:
            task_id: clustering job id.

        Keyword Args:
            userid: the id of the user who calls the tagging.
        """
        job = self.get_clustering_chore(task_id)
        user = User.objects.get(id=userid)

        # get cluster_id to paper mapping
        clusterid_to_papers = self.get_clusterid_to_paper_mapping(task_id)
        clusterid_to_name = self.get_cluster_name_map(task_id)

        # get tag_texts
        tag_texts = [
            self._format_cluster_tag_text(task_id, cid, clusterid_to_name.get(cid, ""))
            for cid in clusterid_to_papers.keys()
        ]

        # get/create tags
        tags = MarkingTaskService.bulk_get_or_create_tag(tag_texts, user=user)

        # cluster_id to tag.pk
        cid_to_tag = {self._get_cluster_id_from_cluster_tag(t.text): t for t in tags}

        # get paper_num to tag.pk
        paper_num_to_tag_pk = {
            paper.paper_number: cid_to_tag[cid].pk
            for cid, papers in clusterid_to_papers.items()
            for paper in papers
        }

        self._remove_cluster_tag_links(
            job,
            {paper.pk for papers in clusterid_to_papers.values() for paper in papers},
        )

        # fetch all tasks
        task_tuples = MarkingTask.objects.filter(
            question_index=job.question_idx,
            question_version=job.version,
            paper__paper_number__in=paper_num_to_tag_pk.keys(),
        ).values_list("pk", "paper__paper_number")

        # use through for efficient bulk operation
        Through = MarkingTaskTag.task.through
        rows = [
            Through(markingtasktag_id=paper_num_to_tag_pk[pnum], markingtask_id=task_pk)
            for task_pk, pnum in task_tuples
        ]

        # Insert once
        Through.objects.bulk_create(rows, ignore_conflicts=True)

    @classmethod
    def _format_cluster_tag_text(
        cls, task_id: int, clusterId: int, cluster_name: str
    ) -> str:
        """Build the generated tag text for a cluster."""
        tag_text = f"cluster_job{task_id}_{clusterId}"
        clean_name = cls._cluster_name_to_tag_suffix(cluster_name)
        if clean_name:
            tag_text = f"{tag_text}_{clean_name}"
        return tag_text

    @classmethod
    def _cluster_name_to_tag_suffix(cls, cluster_name: str) -> str:
        """Convert a cluster name to a valid tag suffix."""
        clean_name = cluster_name.strip()
        if not clean_name:
            return ""

        clean_name = cls._INVALID_CLUSTER_TAG_NAME_CHARS_RE.sub("_", clean_name)
        return clean_name.strip("_")

    def remove_tag_from_a_cluster(self, task_id: int, clusterId: int, tag_pk: int):
        """Remove a tag identified with tag_pk from all tasks in the cluster.

        Args:
            task_id: clustering job id.
            clusterId: identifier of the cluster.
            tag_pk: the primary key of the tag to be removed from the cluster.
        """
        # Get all tasks in the cluster
        tasks = self.get_all_tasks_in_a_cluster(task_id, clusterId)

        # get all relevant MarkingTaskTag
        task_tags = MarkingTaskTag.objects.filter(task__in=tasks, id=tag_pk)

        task_tags.delete()

    def _get_cluster_id_from_cluster_tag(self, cluster_tag_text: str) -> int:
        """Get the cluster id given a cluster tag.

        Args:
            cluster_tag_text: the text of the cluster tag, currently following the format
                of cluster_job{task_id}_{clusterId}.

        Returns:
            the clusterId parsed from the cluster tag text.
        """
        match = self._CLUSTER_TAG_RE.match(cluster_tag_text)
        if not match:
            raise ValueError(f"Invalid cluster tag text: {cluster_tag_text}")
        return int(match.group(1))

    def get_all_tasks_in_a_cluster(
        self, task_id: int, clusterId: int
    ) -> QuerySet[MarkingTask]:
        """Get all tasks in a cluster.

        Args:
            task_id: clustering job id.
            clusterId: the identifier of the cluster.

        Returns:
            QuerySet of all MarkingTask in the queried cluster.
        """
        job = self.get_clustering_chore(task_id)
        paper_nums = self.get_paper_nums_in_clusters(task_id)[clusterId]
        return MarkingTask.objects.filter(
            question_index=job.question_idx,
            question_version=job.version,
            paper__paper_number__in=set(paper_nums),
        )

    @transaction.atomic
    def cluster_ids_to_tags(self, task_id: int) -> dict[int, set[tuple[int, str]]]:
        """Return a mapping from clusterId to a set of tags in the cluster.

        NOTE: The tags that are included in the set are those that are shared across all tasks
            within the cluster.

        Args:
            task_id: clustering job id.

        Returns:
            A mapping from clusterId to a set of tags shared across all tasks in the cluster.
            Each tag is represented as (tag.pk, tag.text).
        """
        job = self.get_clustering_chore(task_id)
        # cluster -> papers
        cluster_to_papers = self.get_clusterid_to_paper_mapping(task_id)
        paper_nums = [p.paper_number for ps in cluster_to_papers.values() for p in ps]

        # Fetch all tasks (with tags) in one go
        tasks = (
            MarkingTask.objects.filter(
                question_index=job.question_idx,
                question_version=job.version,
                paper__paper_number__in=paper_nums,
            )
            .select_related(
                "paper"
            )  # so we can read paper_number without extra queries
            .prefetch_related("markingtasktag_set")
        )

        # paper_id -> list[task]
        paper_to_tasks = defaultdict(list)
        for t in tasks:
            paper_to_tasks[t.paper.paper_number].append(t)

        # cluster_id -> set of tag tuples (pk, text) that are common across ALL tasks
        cluster_to_common_tag: dict[int, set[tuple[int, str]]] = {}

        for cid, papers in cluster_to_papers.items():
            # Get all tasks for this cluster (via its papers)
            task_list = []
            for p in papers:
                task_list.extend(paper_to_tasks.get(p.paper_number, []))

            if not task_list:
                cluster_to_common_tag[cid] = set()
                continue

            # Start with tags from first task, then intersect
            common = {(tg.pk, tg.text) for tg in task_list[0].markingtasktag_set.all()}
            for t in task_list[1:]:
                common = common.intersection(
                    {(tg.pk, tg.text) for tg in t.markingtasktag_set.all()}
                )  # set intersection

            cluster_to_common_tag[cid] = common

        return cluster_to_common_tag

    def get_corners_used_for_clustering(self, task_id: int) -> dict[str, float]:
        """Get the rectangle used for clustering in a (q, v) context.

        Args:
            task_id: clustering job id.

        Returns:
            A dict representing the rectangular region and has these
            keys: [top, left, bottom, right].

        Raises:
            ObjectDoesNotExist: if there is no clustering data or job for the
                question/version.
        """
        task = self.get_clustering_chore(task_id)
        return {
            "top": task.top,
            "left": task.left,
            "bottom": task.bottom,
            "right": task.right,
        }

    def _get_merged_component(self, task_id: int, clusterId: int):
        qs = QVCluster.objects.get(
            job_id=task_id,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        ).original_cluster.all()

        return qs

    def get_merged_component_count(self, task_id: int) -> dict[int, int]:
        """Get a mapping from clusterId to the count of count of merged components.

        Args:
            task_id: clustering job id.

        Returns:
            A dict mapping clusterId to count of merged clusters.
        """
        return {
            cluster.clusterId: len(
                self._get_merged_component(task_id, cluster.clusterId)
            )
            for cluster in QVCluster.objects.filter(
                job_id=task_id,
                type=ClusteringGroupType.user_facing,
            )
        }

    @transaction.atomic
    def merge_clusters(self, task_id: int, clusterIds: list[int]) -> int:
        """Merge all clusters in clusterIDs within a (q, v) context.

        NOTE: the resulting cluster is the cluster of minimum ID.

        Args:
            task_id: clustering job id.
            clusterIds: the identifier of the clusters to be merged.

        Returns:
            Cluster id of the merged clusters.

        Raises:
            EmptySelectedError: if attempting to merge 0 cluster
        """
        if len(clusterIds) == 0:
            raise EmptySelectedError("attempting to merge empty clusters")

        # Check if clusters have conflicting tags:
        cluster_to_tags = self.cluster_ids_to_tags(task_id)

        clusterIdSet = set(clusterIds)
        for clusterId, tag in cluster_to_tags.items():
            if clusterId in clusterIdSet and tag != cluster_to_tags[clusterIds[0]]:
                raise ValueError("Merge failed: there are conflicting tags")

        # assign to the minimum clusterId
        target_cluster_id = min(clusterIds)
        target_cluster = QVCluster.objects.get(
            job_id=task_id,
            clusterId=target_cluster_id,
            type=ClusteringGroupType.user_facing,
        )

        clusters_to_merge = QVCluster.objects.filter(
            job_id=task_id,
            clusterId__in=set(clusterIds),
            type=ClusteringGroupType.user_facing,
        )

        # reassign cluster membership
        QVClusterLink.objects.filter(qv_cluster__in=set(clusters_to_merge)).update(
            qv_cluster=target_cluster
        )

        QVCluster.objects.filter(
            type=ClusteringGroupType.original, user_cluster__in=clusters_to_merge
        ).update(user_cluster=target_cluster)

        # remove obsolete cluster groups
        clusters_to_merge.exclude(clusterId=target_cluster_id).delete()
        return target_cluster_id

    @transaction.atomic
    def delete_clusters(self, task_id: int, clusterIds: list[int]) -> None:
        """Delete clusters in clusterIds in a (q, v) context.

        Args:
            task_id: clustering job id.
            clusterIds: the identifier of the clusters to be deleted.

        Raises:
            EmptySelectedError: if attempts to delete 0 cluster.
        """
        if len(clusterIds) == 0:
            raise EmptySelectedError("attempting to delete 0 cluster")
        QVCluster.objects.filter(
            job_id=task_id,
            clusterId__in=set(clusterIds),
            type=ClusteringGroupType.user_facing,
        ).delete()

    @transaction.atomic
    def delete_cluster_member(
        self, task_id: int, clusterId: int, paper_num: int
    ) -> int:
        """Remove a paper from a cluster.

        Args:
            task_id: clustering job id.
            clusterId: the id of the cluster whose member will be removed.
            paper_num: the paper number of the paper to be removed from the cluster.

        Raises:
            ObjectDoesNOTExist: paper_num is not a valid paper_number or (q, v, clusterId) is not a valid
                cluster, or the paper is not part of the cluster.

        Returns:
            the count of member in the cluster post-removal.
        """
        paper = Paper.objects.get(paper_number=paper_num)
        qvc = QVCluster.objects.get(
            job_id=task_id,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        qvc.paper.remove(paper)

        member_count = len(qvc.paper.all())

        return member_count

    @transaction.atomic
    def bulk_delete_cluster_members(
        self, task_id: int, clusterId: int, paper_nums: list[int]
    ) -> int:
        """Bulk remove paper_nums from a cluster.

        NOTE: this function is optimized to avoid N+1 queries, such that it avoids
            calling delete_cluster_member.

        Args:
            task_id: clustering job id.
            clusterId: the id of the cluster whose members will be deleted.
            paper_nums: the paper numbers of those to be removed from the cluster.

        Raises:
            ObjectDoesNOTExist: paper_num is not a valid paper_number or (q, v, clusterId) is not a valid
                cluster, or the paper is not part of the cluster.
            EmptySelectedError: if attempt to delete call delete on 0 paper_nums.

        Returns:
            The count of the members in the cluster post-removal.
        """
        if len(paper_nums) == 0:
            raise EmptySelectedError("attempting to remove 0 paper from cluster.")

        papers_to_remove = Paper.objects.filter(paper_number__in=set(paper_nums))

        qvc = QVCluster.objects.get(
            job_id=task_id,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )

        qvc.paper.remove(*papers_to_remove)

        member_count = len(qvc.paper.all())

        return member_count

    @transaction.atomic
    def reset_clusters(self, task_id: int) -> list[int]:
        """Reset all clusters for a job back to the original clustering.

        Args:
            task_id: clustering job id.

        Raises:
            ObjectDoesNotExist: if there is no original clustering to restore.

        Returns:
            Sorted list of affected original cluster ids restored by the reset.
        """
        job = self.get_clustering_chore(task_id)
        original_clusters = list(
            QVCluster.objects.filter(
                job=job,
                type=ClusteringGroupType.original,
            ).prefetch_related("paper")
        )

        if not original_clusters:
            raise ObjectDoesNotExist(
                "No original clustering exists for this question/version."
            )

        user_cluster_by_cluster_id = {
            cluster.clusterId: cluster
            for cluster in QVCluster.objects.filter(
                job=job,
                type=ClusteringGroupType.user_facing,
            )
        }
        target_cluster_by_original_pk: dict[int, QVCluster] = {}
        clusters_to_restore_metadata = []

        for original in original_clusters:
            target_cluster = user_cluster_by_cluster_id.get(original.clusterId)
            if target_cluster is None:
                target_cluster = QVCluster.objects.create(
                    question_idx=original.question_idx,
                    version=original.version,
                    job=job,
                    clusterId=original.clusterId,
                    type=ClusteringGroupType.user_facing,
                    page_num=original.page_num,
                    top=original.top,
                    left=original.left,
                    bottom=original.bottom,
                    right=original.right,
                )
                user_cluster_by_cluster_id[original.clusterId] = target_cluster
            else:
                target_cluster.cluster_name = ""
                target_cluster.page_num = original.page_num
                target_cluster.top = original.top
                target_cluster.left = original.left
                target_cluster.bottom = original.bottom
                target_cluster.right = original.right
                clusters_to_restore_metadata.append(target_cluster)

            target_cluster_by_original_pk[original.pk] = target_cluster

        if clusters_to_restore_metadata:
            QVCluster.objects.bulk_update(
                clusters_to_restore_metadata,
                ["cluster_name", "page_num", "top", "left", "bottom", "right"],
            )

        current_user_paper_ids = set(
            QVClusterLink.objects.filter(
                qv_cluster__job=job,
                qv_cluster__type=ClusteringGroupType.user_facing,
            ).values_list("paper_id", flat=True)
        )

        original_paper_ids_by_original_pk = {
            original.pk: {paper.pk for paper in original.paper.all()}
            for original in original_clusters
        }
        affected_paper_ids = set(current_user_paper_ids)
        for paper_ids in original_paper_ids_by_original_pk.values():
            affected_paper_ids.update(paper_ids)

        self._remove_cluster_tag_links(job, affected_paper_ids)

        QVClusterLink.objects.filter(
            qv_cluster__job=job,
            qv_cluster__type=ClusteringGroupType.user_facing,
        ).delete()

        links = []
        for original in original_clusters:
            target_cluster = target_cluster_by_original_pk[original.pk]
            for paper_id in original_paper_ids_by_original_pk[original.pk]:
                links.append(
                    QVClusterLink(paper_id=paper_id, qv_cluster=target_cluster)
                )
        if links:
            QVClusterLink.objects.bulk_create(links)

        originals_to_update = []
        for original in original_clusters:
            target_cluster = target_cluster_by_original_pk[original.pk]
            if original.user_cluster_id != target_cluster.pk:
                original.user_cluster = target_cluster
                originals_to_update.append(original)
        if originals_to_update:
            QVCluster.objects.bulk_update(originals_to_update, ["user_cluster"])

        original_cluster_ids = {original.clusterId for original in original_clusters}
        QVCluster.objects.filter(
            job=job,
            type=ClusteringGroupType.user_facing,
        ).exclude(clusterId__in=original_cluster_ids).delete()

        self._delete_empty_manual_clusters(task_id)

        return sorted(original_cluster_ids)

    def _delete_empty_manual_clusters(self, task_id: int) -> None:
        """Delete empty user-facing clusters that no original cluster points to."""
        QVCluster.objects.filter(
            job_id=task_id,
            type=ClusteringGroupType.user_facing,
        ).annotate(
            paper_count=Count("paper"),
            original_count=Count("original_cluster"),
        ).filter(
            paper_count=0,
            original_count=0,
        ).delete()

    def _remove_cluster_tag_links(
        self, job: QuestionClusteringChore, paper_ids: set[int]
    ) -> None:
        """Remove generated cluster tag links from affected marking tasks."""
        if not paper_ids:
            return

        tasks = MarkingTask.objects.filter(
            question_index=job.question_idx,
            question_version=job.version,
            paper_id__in=paper_ids,
        )
        Through = MarkingTaskTag.task.through
        Through.objects.filter(
            markingtask__in=tasks,
            markingtasktag__text__startswith=f"cluster_job{job.pk}_",
        ).delete()


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_cluster_single_qv(
    question_idx: int,
    version: int,
    page_num: int,
    rect: dict,
    clustering_model: ClusteringModelType,
    *,
    tracker_pk: int,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Build a cluster mapping for a single clustering job.

    Args:
        question_idx: The question to be clustered on.
        version: version of the question to be clustered on.
        page_num: page_num for the clustering, used to resolve ambiguity in multi-pages question.
        rect: dict of coordinates of the rectangle used for clustering. Ideally should primarily
        contain final answer.
        clustering_model: the model used for the clustering

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    assert task is not None

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)
    clustering_job = QuestionClusteringChore.objects.get(pk=tracker_pk)
    qcs = QuestionClusteringService()
    qcs.cluster_qv(
        clustering_job,
        question_idx,
        version,
        page_num,
        rect,
        clustering_model,
        mcq_metadata=clustering_job.mcq_metadata,
    )

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
