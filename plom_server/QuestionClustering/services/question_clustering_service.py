# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom_server.QuestionClustering.models import (
    QuestionClusteringChore,
    QVClusterLink,
    QVCluster,
    ClusteringGroupType,
)

from plom_server.Papers.models import Paper
from plom_server.Papers.services import PaperInfoService
from plom_server.Rectangles.services import (
    RectangleExtractor,
)
from plom_server.Base.models import HueyTaskTracker
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django_huey import db_task
import huey
import huey.api
import numpy as np
from .image_processing_service import ImageProcessingService
from .clustering_pipeline import ClusteringPipeline
from .preprocessor import DiffProcessor
import cv2
from django.db.models import Count
from plom_server.QuestionClustering.models import ClusteringModelType
from django.db import transaction
from plom_server.Mark.services.marking_priority import (
    get_tasks_to_update_priority,
    modify_task_priority,
)
from plom_server.Base.models import User
from plom_server.Mark.models import MarkingTask, MarkingTaskTag
from plom_server.Mark.services.marking_task_service import MarkingTaskService
from typing import Optional
from collections import defaultdict
from typing import Any
from django.forms.models import model_to_dict


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
                    clusterId=clusterId,
                    type=ClusteringGroupType.user_facing,
                    page_num=page_num,
                    top=rects["top"],
                    left=rects["left"],
                    bottom=rects["bottom"],
                    right=rects["right"],
                )

                base_cluster = QVCluster.objects.create(
                    question_idx=question_idx,
                    version=version,
                    clusterId=clusterId,
                    type=ClusteringGroupType.original,
                    page_num=page_num,
                    top=rects["top"],
                    left=rects["left"],
                    bottom=rects["bottom"],
                    right=rects["right"],
                    user_cluster=user_facing_cluster,
                )

                # Use .filter instead of .get in for loop to avoid n+1 queries
                papers = Paper.objects.filter(paper_number__in=paper_nums)
                base_cluster.paper.add(*papers)
                user_facing_cluster.paper.add(*papers)

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
        # return [
        #     {
        #         "question_idx": task.question_idx,
        #         "version": task.version,
        #         "page_num": task.page_num,
        #         "status": task.get_status_display(),
        #         "message": task.message
        #     }
        #     for task in QuestionClusteringChore.objects.filter(obsolete=False)
        # ]

        temp = []
        for task in QuestionClusteringChore.objects.filter(obsolete=False):
            temp.append(
                {
                    "task_id": task.id,
                    "question_idx": task.question_idx,
                    "version": task.version,
                    "page_num": task.page_num,
                    "status": task.get_status_display(),
                    "message": task.message,
                }
            )

        return temp

    def get_user_facing_clusters(self, question_idx: int, version: int) -> dict:
        """Get a mapping of clusterId to the count of the members"""
        qs = (
            QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                type=ClusteringGroupType.user_facing,
            )
            .annotate(count=Count("paper"))
            .values("clusterId", "count")
            .order_by("clusterId")
        )
        return {item["clusterId"]: item["count"] for item in qs}

    def get_paper_nums_in_clusters(
        self, question_idx: int, version: int
    ) -> dict[int, list[int]]:
        """Get a mapping from clusterId to the paper_num of papers under the given cluster"""
        qs = QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        result = {}
        for item in qs:
            cluster_id = item.clusterId
            result[cluster_id] = [paper.paper_number for paper in item.paper.all()]

        return result

    def get_cluster_priority(
        self, question_idx: int, version: int, clusterId: int
    ) -> Optional[float]:

        papers = QVCluster.objects.get(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        ).paper.all()
        all_tasks = get_tasks_to_update_priority().filter(
            question_index=question_idx, question_version=version
        )
        unique_priorities = (
            all_tasks.filter(paper__in=papers)
            .values_list("marking_priority", flat=True)
            .distinct()
        )
        return unique_priorities[0] if len(unique_priorities) == 1 else None

    def get_cluster_priority_map(
        self, question_idx: int, version: int
    ) -> dict[int, Optional[float]]:
        """Get the mapping of cluster id to priority values.

        Note: If there exists tasks under same cluster with conflicting priorities, the priority
            is set to None

        Returns:
            A dict mapping clusterId to the priority val. Priority val is None if there are task
            priorities under the same cluster"""

        return {
            cluster.clusterId: self.get_cluster_priority(
                question_idx, version, cluster.clusterId
            )
            for cluster in QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                type=ClusteringGroupType.user_facing,
            )
        }

    def update_priority_based_on_scene(
        self, cluster_order: list[int], question_idx: int, version: int
    ):
        """Update priority values based on the cluster table's order.

        Note: the priority valus is given in the range of [0, len(cluster_order)],
            priority 0 is given to the papers that are not part of any clsuters

        cluster_order: a list of clusterIds sorted based on decreasing priority.
        """
        # grab the relevant clusters in a (q, v) context
        clusters = QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        # grab all tasks
        tasks = get_tasks_to_update_priority().filter(
            question_index=question_idx, question_version=version
        )

        clustered_papers = set()

        for i, clusterId in enumerate(cluster_order):
            # get the relevant tasks for every cluster
            curr_cluster = clusters.get(clusterId=clusterId)
            curr_papers = curr_cluster.paper.all()
            curr_tasks = tasks.filter(paper__in=curr_papers)

            # update all tasks under that cluster to the same priority val
            priority = len(cluster_order) - i
            for task in curr_tasks:
                modify_task_priority(task, priority)

            clustered_papers.update(p.pk for p in curr_papers)

        # update priority for paper not part of any cluster to 0
        task_not_in_cluster = tasks.exclude(paper__in=clustered_papers)
        for task in task_not_in_cluster:
            modify_task_priority(task, 0)

    def get_clusterid_to_paper_mapping(
        self, question_idx: int, version: int
    ) -> dict[int, list[Paper]]:
        """Get a dict mapping clusterId to list of papers under a q,v contenxt."""
        clusters = QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        return {cluster.clusterId: list(cluster.paper.all()) for cluster in clusters}

    @transaction.atomic
    def bulk_tagging(self, question_idx: int, version: int, userid: int):
        """Bulk tag all clusters with default cluster tag.

        Note: current default cluster tag is cluster_{question_idx}_{version}_{clusterId}.
        """
        mts = MarkingTaskService()
        user = User.objects.get(id=userid)

        # get cluster_id to paper mapping
        clusterid_to_papers = self.get_clusterid_to_paper_mapping(question_idx, version)

        # get tag_texts
        tag_texts = [
            f"cluster_{question_idx}_{version}_{cid}"
            for cid in clusterid_to_papers.keys()
        ]

        # get/create tags
        tags = mts.bulk_get_or_create_tag(user=user, tag_texts=tag_texts)

        # cluster_id to tag.pk
        cid_to_tag = {self._get_cluster_id_from_cluster_tag(t.text): t for t in tags}

        # get paper_num to tag.pk
        paper_num_to_tag_pk = {
            paper.paper_number: cid_to_tag[cid].pk
            for cid, papers in clusterid_to_papers.items()
            for paper in papers
        }

        # fetch all tasks
        task_tuples = MarkingTask.objects.filter(
            question_index=question_idx,
            question_version=version,
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

    def remove_tag_from_a_cluster(
        self, question_idx: int, version: int, clusterId: int, tag_pk: int
    ):
        # Get all tasks in the cluster
        tasks = self.get_all_tasks_in_a_cluster(question_idx, version, clusterId)

        # get all relevant MarkingTaskTag
        task_tags = MarkingTaskTag.objects.filter(task__in=tasks, id=tag_pk)

        task_tags.delete()

    def _get_cluster_id_from_cluster_tag(self, cluster_tag_text: str) -> int:
        return int(cluster_tag_text.rsplit("_", 1)[-1])

    def get_all_tasks_in_a_cluster(
        self, question_idx: int, version: int, clusterId: int
    ):
        paper_nums = self.get_paper_nums_in_clusters(
            question_idx=question_idx, version=version
        )[clusterId]
        return MarkingTask.objects.filter(
            question_index=question_idx,
            question_version=version,
            paper__paper_number__in=set(paper_nums),
        )

    @transaction.atomic
    def cluster_ids_to_tags(
        self, question_idx: int, version: int
    ) -> dict[int, list[tuple[int, str]]]:
        """Return {cluster_id: [(tag_pk, tag_text), ...]} where each tag appears on **every MarkingTask in that cluster**."""

        # cluster -> papers
        cluster_to_papers = self.get_clusterid_to_paper_mapping(question_idx, version)
        paper_nums = [p.paper_number for ps in cluster_to_papers.values() for p in ps]

        # Fetch all tasks (with tags) in one go
        tasks = (
            MarkingTask.objects.filter(
                question_index=question_idx,
                question_version=version,
                paper_id__in=paper_nums,
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
        cluster_to_common = {}

        for cid, papers in cluster_to_papers.items():
            # Get all tasks for this cluster (via its papers)
            task_list = []
            for p in papers:
                task_list.extend(paper_to_tasks.get(p.id, []))

            if not task_list:
                cluster_to_common[cid] = []
                continue

            # Start with tags from first task, then intersect
            common = {(tg.pk, tg.text) for tg in task_list[0].markingtasktag_set.all()}
            for t in task_list[1:]:
                common &= {
                    (tg.pk, tg.text) for tg in t.markingtasktag_set.all()
                }  # set intersection

            cluster_to_common[cid] = common

        return cluster_to_common

    def get_corners_used_for_clustering(self, question_idx: int, version: int):
        qvc = QVCluster.objects.filter(question_idx=question_idx, version=version)[0]
        return {
            "top": qvc.top,
            "left": qvc.left,
            "bottom": qvc.bottom,
            "right": qvc.right,
        }

    def _get_merged_component(self, question_idx: int, version: int, clusterId: int):
        qs = QVCluster.objects.get(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        ).original_cluster.all()

        return qs

    def get_merged_component_count(self, question_idx: int, version: int):
        return {
            cluster.clusterId: len(
                self._get_merged_component(question_idx, version, cluster.clusterId)
            )
            for cluster in QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                type=ClusteringGroupType.user_facing,
            )
        }

    def merge_clusters(self, question_idx: int, version: int, clusterIds: list[int]):
        if not clusterIds:
            return

        with transaction.atomic():
            # Check if clusters have conflicting tags:
            cluster_to_tags = self.cluster_ids_to_tags(question_idx, version)
            ref = cluster_to_tags[0]

            clusterIdSet = set(clusterIds)
            for clusterId, tag in cluster_to_tags.items():
                if clusterId in clusterIdSet and tag != cluster_to_tags[clusterIds[0]]:
                    raise ValueError("Merge failed: there are conflicting tags")

            # assign to the minimum clusterId
            target_cluster_id = min(clusterIds)
            target_cluster = QVCluster.objects.get(
                question_idx=question_idx,
                version=version,
                clusterId=target_cluster_id,
                type=ClusteringGroupType.user_facing,
            )

            clusters_to_merge = QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
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

    def delete_clusters(self, question_idx: int, version: int, clusterIds: list[int]):
        with transaction.atomic():

            # BaseQVCluster.objects.filter(
            #     question_idx=question_idx,
            #     version=version,
            #     clusterId__in=set(clusterIds),
            # ).delete()

            QVCluster.objects.filter(
                question_idx=question_idx,
                version=version,
                clusterId__in=set(clusterIds),
                type=ClusteringGroupType.user_facing,
            ).delete()

    def delete_cluster_member(
        self, question_idx: int, version: int, clusterId: int, paper_num: int
    ):
        paper = Paper.objects.get(paper_number=paper_num)
        qvc = QVCluster.objects.get(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        qvc.paper.remove(paper)

    def reset_clusters(self, question_idx: int, version: int, clusterIds: list[int]):
        for cid in clusterIds:
            self._reset_cluster(question_idx, version, cid)

        return len(clusterIds)

    def _reset_cluster(self, question_idx: int, version: int, clusterId: int):
        user_facing_cluster = QVCluster.objects.get(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        # grab base clusters that pointed at this user_facing (UF) cluster
        originals = list(user_facing_cluster.original_cluster.all())

        with transaction.atomic():
            # reset tags
            tasks = self.get_all_tasks_in_a_cluster(question_idx, version, clusterId)
            MarkingTaskTag.objects.filter(
                task__in=tasks, text__startswith=f"cluster_{question_idx}_{version}_"
            ).delete()

            # delete the old UF cluster
            user_facing_cluster.delete()

            # create new UF clusters and collect them
            new_clusters = []
            for oc in originals:
                new = QVCluster.objects.create(
                    question_idx=oc.question_idx,
                    version=oc.version,
                    clusterId=oc.clusterId,
                    type=ClusteringGroupType.user_facing,
                    page_num=oc.page_num,
                    top=oc.top,
                    left=oc.left,
                    bottom=oc.bottom,
                    right=oc.right,
                )
                new_clusters.append(new)

            # copy M2M links in bulk via the through‐model
            links = []
            for new, oc in zip(new_clusters, originals):
                for paper in oc.paper.all():
                    links.append(QVClusterLink(paper=paper, qv_cluster=new))
            QVClusterLink.objects.bulk_create(links)

            # point each original at its matching new UF cluster
            for oc, new in zip(originals, new_clusters):
                oc.user_cluster = new
            QVCluster.objects.bulk_update(originals, ["user_cluster"])

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
