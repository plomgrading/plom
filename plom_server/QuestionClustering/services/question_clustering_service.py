# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom_server.QuestionClustering.models import (
    QuestionClusteringChore,
    QVClusterLink,
    QVCluster,
)

from plom_server.Papers.models import Paper
from plom_server.Papers.services import PaperInfoService
from plom_server.Rectangles.services import (
    RectangleExtractor,
    extract_rect_region_from_image,
)
from plom_server.Base.models import HueyTaskTracker
from django.db import transaction
from django_huey import db_task, get_queue
import huey
import huey.api
import numpy as np
from .image_processing_service import ImageProcessingService
from .clustering_pipeline import ClusteringPipeline
from .preprocessor import DiffProcessor
import cv2
from sklearn.cluster import AgglomerativeClustering
import pandas as pd
from io import BytesIO
from PIL import Image
from django.db.models import Count
from plom_server.QuestionClustering.models import ClusteringModelType
from django.db import transaction


class QuestionClusteringService:

    def start_cluster_qv_job(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        rects: dict,
        clustering_model: ClusteringModelType,
    ):
        """Run a background job to cluster papers for a (q, v) for the given page_num and rects.

        question_idx: The question index used for clustering
        version: The question version used for clustering
        page_num: The page number used for clustering. Note: this is needed as there can be
            multi-pages question
        rects: the coordinates of the four corners of the rectangle used for clustering.
            Rects should have these keys: [top, left, bottom, right].
        clustering_model: the model used to cluster the papers.
        """
        expected_keys = {"top", "left", "bottom", "right"}
        if expected_keys.intersection(set(rects.keys())) != expected_keys:
            raise ValueError(
                f"rects must have these keys: {expected_keys}, but received: {rects.keys()}"
            )

        with transaction.atomic(durable=True):
            x = QuestionClusteringChore.objects.create(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                top=rects["top"],
                left=rects["left"],
                bottom=rects["bottom"],
                right=rects["right"],
                clustering_model=clustering_model,
                status=HueyTaskTracker.STARTING,
            )
            tracker_pk = x.pk

        res = huey_cluster_single_qv(
            question_idx=question_idx,
            version=version,
            page_num=page_num,
            rects=rects,
            tracker_pk=tracker_pk,
            clustering_model=clustering_model,
            _debug_be_flaky=False,
        )
        # print(f"Just enqueued Huey parent_split_and_save task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    def _store_clustered_result(
        self,
        paper_to_clusterId: dict[int, int],
        question_idx: int,
        version: int,
        page_num: int,
        rects,
    ) -> None:
        """Store clustering result to database.

        Args:
            paper-to_cluster_Id: clustering result that maps paper number to their cluster group.
        """
        for pn, clusterId in paper_to_clusterId.items():
            paper = Paper.objects.get(paper_number=pn)
            qv_cluster, _ = QVCluster.objects.get_or_create(
                question_idx=question_idx,
                version=version,
                clusterId=clusterId,
                page_num=page_num,
                top=rects["top"],
                left=rects["left"],
                bottom=rects["bottom"],
                right=rects["right"],
            )
            QVClusterLink.objects.create(paper=paper, qv_cluster=qv_cluster)

    def cluster_mcq(self, question_idx: int, version: int, page_num: int, rects: dict):
        """Cluster mcq responses within the given rects for a qv pair."""
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rects)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # get paper_num to ref, scanned mapping used for clustering input
        paper_to_images = {
            pn: (ref, rex.get_cropped_scanned_img(pn, rects)) for pn in paper_numbers
        }

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            model_type=ClusteringModelType.MCQ,
            preprocessor=DiffProcessor(dilation_strength=1, invert=False),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, question_idx, version, page_num, rects
        )

    def cluster_hme(self, question_idx: int, version: int, page_num: int, rects: dict):
        """Cluster handwritten math responses within the given rects for a qv pair."""
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rects)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # get paper_num to ref, scanned mapping used for clustering input
        paper_to_images = {
            pn: (ref, rex.get_cropped_scanned_img(pn, rects)) for pn in paper_numbers
        }

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            model_type=ClusteringModelType.HME,
            preprocessor=DiffProcessor(dilation_strength=1, invert=True),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, question_idx, version, page_num, rects
        )

    def cluster_qv(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        rects: dict,
        clustering_model: ClusteringModelType,
    ):
        if clustering_model == ClusteringModelType.MCQ:
            self.cluster_mcq(question_idx, version, page_num, rects)

        elif clustering_model == ClusteringModelType.HME:
            self.cluster_hme(question_idx, version, page_num, rects)

    def predict(self, ref: np.ndarray, scanned: np.ndarray) -> list:
        """Predict handwritten answer by outputting vector of probability.

        Args:
            ref:
            scanned:

        Returns:

        """
        gap_tolerance = 10
        num_classes = 11

        imp = ImageProcessingService()
        diff = imp.get_diff(ref, scanned)

        # find raw components
        _, _, stats, _ = cv2.connectedComponentsWithStats(diff, connectivity=8)

        # merge nearby components
        groups = imp.merge_components_by_proximity(stats, tol=gap_tolerance)

        # pick best over each merged group
        bestConfidence, bestProbs = 0.0, [0] * num_classes
        for group in groups:
            # build union-bbox
            xs, ys, ws, hs = [], [], [], []
            for lab in group:
                x, y, w, h, _ = stats[lab]
                xs.append(x)
                ys.append(y)
                ws.append(w)
                hs.append(h)
            x0, y0 = min(xs), min(ys)
            x1 = max(x + w for x, w in zip(xs, ws))
            y1 = max(y + h for y, h in zip(ys, hs))
            area = (x1 - x0) * (y1 - y0)
            if area < 100:
                continue

            crop = diff[y0:y1, x0:x1]
            confidence, probs = self.model.predict(crop, thresh=0.55)
            if confidence > bestConfidence:
                bestConfidence = confidence
                bestProbs = probs

        return bestProbs

    def get_question_clustering_tasks(self) -> list[dict]:
        """Get all non-obsolete clustering tasks.

        Returns:
            A list of dicts each representing a non-obsolete clustering task. The dict
            has these keys: [question_idx, version, status].
        """
        return [
            {
                "question_idx": task.question_idx,
                "version": task.version,
                "page_num": task.page_num,
                "status": task.get_status_display(),
            }
            for task in QuestionClusteringChore.objects.filter(obsolete=False)
        ]

    def get_cluster_groups_and_count(self, question_idx: int, version: int) -> dict:
        """Get."""
        qs = (
            QVClusterLink.objects.filter(
                qv_cluster__question_idx=question_idx, qv_cluster__version=version
            )
            .values("qv_cluster__clusterId")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return {item["qv_cluster__clusterId"]: item["count"] for item in qs}

    def get_paper_nums_in_clusters(self, question_idx: int, version: int):
        qs = QVClusterLink.objects.filter(
            qv_cluster__question_idx=question_idx, qv_cluster__version=version
        ).prefetch_related("paper")

        result = {}
        for item in qs:
            cluster_id = item.qv_cluster.clusterId
            paper_num = item.paper.paper_number

            if cluster_id not in result:
                result[cluster_id] = []
            result[cluster_id].append(paper_num)

        return result

    def get_corners_used_for_clustering(self, question_idx: int, version: int):
        qvc = QVCluster.objects.filter(question_idx=question_idx, version=version)[0]
        return {
            "top": qvc.top,
            "left": qvc.left,
            "bottom": qvc.bottom,
            "right": qvc.right,
        }

    def merge_clusters(self, question_idx: int, version: int, clusterIds: list[int]):
        with transaction.atomic():
            # assign all clusters to an arbritrary cluster id
            target_cluster_id = clusterIds[0]
            target_cluster = QVCluster.objects.get(
                question_idx=question_idx, version=version, clusterId=target_cluster_id
            )

            clusters_to_merge = QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                clusterId__in=set(clusterIds),
            )

            # reassign cluster membership
            QVClusterLink.objects.filter(qv_cluster__in=set(clusters_to_merge)).update(
                qv_cluster=target_cluster
            )

            # remove obsolete cluster groups
            clusters_to_merge.exclude(clusterId=target_cluster_id).delete()

    def delete_clusters(self, question_idx: int, version: int, clusterIds: list[int]):
        with transaction.atomic():

            QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                clusterId__in=set(clusterIds),
            ).delete()

    def delete_cluster_member(
        self, question_idx: int, version: int, clusterId: int, paper_num: int
    ):
        paper = Paper.objects.get(paper_number=paper_num)
        qvc = QVCluster.objects.get(
            question_idx=question_idx, version=version, clusterId=clusterId
        )

        qvcl = QVClusterLink.objects.get(paper=paper, qv_cluster=qvc)
        qvcl.delete()


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_cluster_single_qv(
    question_idx: int,
    version: int,
    page_num: int,
    rects: dict,
    clustering_model: ClusteringModelType,
    *,
    tracker_pk: int,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Build a cluster mapping for a single question, version pair.

    Args:
        question_idx: The question to be clustered on.
        version: version of the question to be clustered on.
        page_num: page_num for the clustering, used to resolve ambiguity in multi-pages question.
        rects: dict of coordinates of the rectangle used for clustering. Ideally should primarily
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
    qcs = QuestionClusteringService()
    qcs.cluster_qv(question_idx, version, page_num, rects, clustering_model)

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
