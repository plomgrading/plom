# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2026 Colin B. Macdonald
# Copyright (C) 2026 Deep Shah

from collections import defaultdict
from typing import Any, Mapping, Optional

# django
from django.forms.models import model_to_dict
from django.db import transaction
from django_huey import db_task
import huey
import huey.api
from django.db.models import Count
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

# exception
from plom_server.QuestionClustering.exceptions.clustering_exception import (
    EmptySelectedError,
)
# plom_ml
from plom_ml.clustering.pipeline.clustering_pipeline import ClusteringPipeline
from plom_ml.clustering.preprocessing.preprocessor import DiffProcessor


class QuestionClusteringJobService:
    """Manage CRUDs of clustering jobs."""

    def start_cluster_qv_job(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
        clustering_model: ClusteringModelType,
    ):
        """Run a background job to cluster papers for the given question region.

        question_idx: The question index used for clustering
        version: The question version used for clustering
        page_num: The page number used for clustering. NOTE: this is needed as there can be
            multi-pages question
        rect: the coordinates of the four corners of the rectangle used for clustering.
            rect should have these keys: [top, left, bottom, right].
        clustering_model: the model used to cluster the papers.

        """
        expected_keys = {"top", "left", "bottom", "right"}
        if expected_keys.intersection(set(rect.keys())) != expected_keys:
            raise ValueError(
                f"rect must have these keys: {expected_keys}, but received: {rect.keys()}"
            )

        with transaction.atomic(durable=True):
            x = QuestionClusteringChore.objects.create(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                top=rect["top"],
                left=rect["left"],
                bottom=rect["bottom"],
                right=rect["right"],
                clustering_model=clustering_model,
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
        task = QuestionClusteringChore.objects.get(id=task_id)
        task.delete()


class QuestionClusteringService:
    """Service handling clustering and querying of cluster-related models."""

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
            question_idx: question index of the clustering context.
            version: version of the clustering context.
            page_num: page used in the clustering.
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

    def cluster_mcq(
        self,
        job: QuestionClusteringChore,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
    ) -> None:
        """Cluster mcq responses within the given rect for a clustering job.

        Args:
            job: clustering job that owns the created clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page_number used for the clustering.
            rect: the rectangular region used for clustering.

        Raises:
            ValueError: problem extracting from reference image.
        """
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rect)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

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
        """Cluster handwritten math expression responses for a clustering job.

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
    ):
        """Run clustering for a job in the given rect with the specified clustering model.

        Args:
            job: clustering job that owns the created clusters.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page num involved in the clustering.
            rect: the rectangular region used for clustering.
            clustering_model: the model used for clustering.

        Raises:
            ValueError: extraction from problem reference image.
        """
        if clustering_model == ClusteringModelType.MCQ:
            self.cluster_mcq(job, question_idx, version, page_num, rect)

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
            A list of tuple of (clusterId, member_count) for all clusters in a job.
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
        """Get a mapping from clusterId to paper nums for a clustering job.

        Args:
            task_id: clustering job id.

        Returns:
            A dict mapping clusterId to paper numbers for all clusters in a job.
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

    def get_cluster_priority(self, task_id: int, clusterId: int) -> Optional[float]:
        """Get the priority value of a cluster in a job.

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
        # grab the relevant clusters in this job
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
        """Get a dict mapping clusterId to papers under a clustering job.

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

        NOTE: current default cluster tag is cluster_job{task_id}_{clusterId}.

        Args:
            task_id: clustering job id.

        Keyword Args:
            userid: the id of the user who calls the tagging.
        """
        job = self.get_clustering_chore(task_id)
        user = User.objects.get(id=userid)

        # get cluster_id to paper mapping
        clusterid_to_papers = self.get_clusterid_to_paper_mapping(task_id)

        # get tag_texts
        tag_texts = [
            f"cluster_job{task_id}_{cid}" for cid in clusterid_to_papers.keys()
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

    def remove_tag_from_a_cluster(
        self, task_id: int, clusterId: int, tag_pk: int
    ):
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
        return int(cluster_tag_text.rsplit("_", 1)[-1])

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
        """Get the rectangle used for a clustering job.

        Args:
            task_id: clustering job id.

        Returns:
            A dict representing the rectangular region and has these
            keys: [top, left, bottom, right].
        """
        job = self.get_clustering_chore(task_id)
        return {
            "top": job.top,
            "left": job.left,
            "bottom": job.bottom,
            "right": job.right,
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
        """Merge all clusters in clusterIDs within a clustering job.

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
        """Delete clusters in clusterIds in a clustering job.

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
    def delete_cluster_member(self, task_id: int, clusterId: int, paper_num: int) -> int:
        """Remove a paper from a cluster.

        Args:
            task_id: clustering job id.
            clusterId: the id of the cluster whose member will be removed.
            paper_num: the paper number of the paper to be removed from the cluster.

        Raises:
            ObjectDoesNOTExist: paper_num is not a valid paper_number or (job, clusterId) is not a valid
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
            ObjectDoesNOTExist: paper_num is not a valid paper_number or (job, clusterId) is not a valid
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

    def reset_clusters(self, task_id: int, clusterIds: list[int]) -> None:
        """Reset all cluster in clusterIds to their original state.

        NOTE: This also resets the state of the papers in the clusters and cluster tag.

        Args:
            task_id: clustering job id.
            clusterIds: the list of Ids of clusters to be reset.

        Raises:
            EmptySelectedError: attempts to reset 0 cluster.
        """
        if not clusterIds:
            raise EmptySelectedError("attempting to reset 0 cluster.")

        for cid in clusterIds:
            self._reset_cluster(task_id, cid)

    def _reset_cluster(self, task_id: int, clusterId: int) -> None:
        """Reset the cluster identified by the (job, clusterId).

        NOTE: This also resets the state of the papers in the cluster and remove cluster tag.

        Args:
            task_id: clustering job id.
            clusterId: the identifier of the cluster to be reset.
        """
        job = self.get_clustering_chore(task_id)
        user_facing_cluster = QVCluster.objects.get(
            job=job,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        # grab base clusters that pointed at this user_facing (UF) cluster
        originals = list(user_facing_cluster.original_cluster.all())

        with transaction.atomic():
            # reset tags
            tasks = self.get_all_tasks_in_a_cluster(task_id, clusterId)
            MarkingTaskTag.objects.filter(
                task__in=tasks, text__startswith=f"cluster_job{task_id}_"
            ).delete()

            # delete the old UF cluster
            user_facing_cluster.delete()

            # create new UF clusters and collect them
            new_clusters = []
            for oc in originals:
                new = QVCluster.objects.create(
                    question_idx=oc.question_idx,
                    version=oc.version,
                    job=job,
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
    qcs = QuestionClusteringService()
    clustering_job = QuestionClusteringChore.objects.get(pk=tracker_pk)
    qcs.cluster_qv(
        clustering_job,
        question_idx,
        version,
        page_num,
        rect,
        clustering_model,
    )

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
