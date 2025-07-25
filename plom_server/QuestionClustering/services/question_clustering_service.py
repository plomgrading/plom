# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# django
from django.forms.models import model_to_dict
from django.db import transaction
from django_huey import db_task
import huey
import huey.api
from django.db.models import Count
from django.db.models import QuerySet

# plom models
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
from plom_server.Mark.services.marking_priority import (
    get_tasks_to_update_priority,
    modify_task_priority,
)
from plom_server.Papers.services import PaperInfoService
from plom_server.Rectangles.services import (
    RectangleExtractor,
)

# exception
from plom_server.QuestionClustering.exceptions.clustering_exception import (
    EmptySelectedError,
)
from plom_server.QuestionClustering.exceptions.job_exception import (
    DuplicateClusteringJobError,
)

# ML
from plom_ml.clustering.clustering_pipeline import ClusteringPipeline
from plom_ml.clustering.preprocessor import DiffProcessor

# misc
from typing import Optional
from collections import defaultdict
from typing import Any


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
        """Run a background job to cluster papers for a (q, v) for the given page_num and rect.

        question_idx: The question index used for clustering
        version: The question version used for clustering
        page_num: The page number used for clustering. NOTE: this is needed as there can be
            multi-pages question
        rect: the coordinates of the four corners of the rectangle used for clustering.
            rect should have these keys: [top, left, bottom, right].
        clustering_model: the model used to cluster the papers.

        Raises:
            DuplicateClusteringJobError if there is existing non-obsolete clustering job for that question, version.
        """
        expected_keys = {"top", "left", "bottom", "right"}
        if expected_keys.intersection(set(rect.keys())) != expected_keys:
            raise ValueError(
                f"rect must have these keys: {expected_keys}, but received: {rect.keys()}"
            )

        with transaction.atomic(durable=True):
            # Check if there exists non-obsolete clustering job for current q,v
            if QuestionClusteringChore.objects.filter(
                question_idx=question_idx, version=version, obsolete=False
            ).exists():
                raise DuplicateClusteringJobError(
                    f"clustering job for q{question_idx}, v{version} already exists"
                )

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
        """Remove a clustering job, and remove the clusterings involved if the job is non-obsolete.

        NOTE: We restrict clustering removal to non_obsolete jobs to avoid unexpected
            removals clusterings.

        Args:
            task_id: the id of the clustering task to be removed.

        Raises:
            ObjectDoesNOTExist: If the task does not exist.
        """
        task = QuestionClusteringChore.objects.get(id=task_id)

        # remove clustering involved in it if task is non-obsolete
        if not task.obsolete:
            question_idx = task.question_idx
            version = task.version
            QVCluster.objects.filter(
                question_idx=question_idx, version=version
            ).delete()

        task.delete()


class QuestionClusteringService:
    """Service handling clustering and querying of cluster-related models."""

    def _store_clustered_result(
        self,
        paper_to_clusterId: dict[int, int],
        question_idx: int,
        version: int,
        page_num: int,
        rect,
    ) -> None:
        """Store clustering result to database.

        Args:
            paper_to_clusterId: a mapping from paper_number to clusterId.
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

    def cluster_mcq(self, question_idx: int, version: int, page_num: int, rect: dict):
        """Cluster mcq responses within the given rect for (q, v) context.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page_number used for the clustering.
            rect: the rectangular region used for clustering.
        """
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rect)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # get paper_num to ref, scanned mapping used for clustering input
        paper_to_images = {
            pn: (ref, rex.get_cropped_scanned_img(pn, rect)) for pn in paper_numbers
        }

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            model_type=ClusteringModelType.MCQ,
            preprocessor=DiffProcessor(dilation_strength=1, invert=False),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, question_idx, version, page_num, rect
        )

    def cluster_hme(self, question_idx: int, version: int, page_num: int, rect: dict):
        """Cluster handwritten math expression responses within the given rect for (q, v) context.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page_number used for the clustering.
            rect: the rectangular region used for clustering.
        """
        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref = rex.get_cropped_ref_img(rect)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # get paper_num to ref, scanned mapping used for clustering input
        paper_to_images = {
            pn: (ref, rex.get_cropped_scanned_img(pn, rect)) for pn in paper_numbers
        }

        # run clustering pipeline
        clustering_pipeline = ClusteringPipeline(
            model_type=ClusteringModelType.HME,
            preprocessor=DiffProcessor(dilation_strength=1, invert=True),
        )
        paper_to_clusterId = clustering_pipeline.cluster(paper_to_images)

        # store clustered results into db
        self._store_clustered_result(
            paper_to_clusterId, question_idx, version, page_num, rect
        )

    def cluster_qv(
        self,
        question_idx: int,
        version: int,
        page_num: int,
        rect: dict,
        clustering_model: ClusteringModelType,
    ):
        """Run clustering on a (q, v) in the given rect with the specified clustering model.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            page_num: the page num involved in the clustering.
            rect: the rectangular region used for clustering.
            clustering_model: the model used for clustering.
        """
        if clustering_model == ClusteringModelType.MCQ:
            self.cluster_mcq(question_idx, version, page_num, rect)

        elif clustering_model == ClusteringModelType.HME:
            self.cluster_hme(question_idx, version, page_num, rect)

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

    def get_clusters_and_member_count(
        self, question_idx: int, version: int
    ) -> list[tuple]:
        """Get a a list of (clusterId, member_count) for all clusters in a (q, v) context.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A list of tuple of (clusterId, member_count) for all clsuters in a (q, v) context.
            The list is sorted by clusterId
        """
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

        return [(q["clusterId"], q["count"]) for q in qs]

    def get_paper_nums_in_clusters(
        self, question_idx: int, version: int
    ) -> dict[int, list[int]]:
        """Get a mapping from clusterId to the paper_num of papers under the given cluster.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A dict mapping clusterId to a list of paper_numbers for all clusters in a (q, v) context.
        """
        qs = QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        result = {
            item.clusterId: [paper.paper_number for paper in item.paper.all()]
            for item in qs
        }

        return result

    def get_cluster_priority(
        self, question_idx: int, version: int, clusterId: int
    ) -> Optional[float]:
        """Get the priority value of a cluster in a (q, v) context.

        NOTE: If there exists some tasks with different priority values then the priority is None.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterId: the id of the cluster in query.

        Returns:
            Priority value of all the tasks in the cluster. If there exists some tasks with different
            priority values then returns None.
        """
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
        """Get the mapping of cluster id to priority value.

        NOTE: If there exists tasks under same cluster with conflicting priorities, the priority
            is set to None

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A dict mapping clusterId to the priority val. Priority val is None if there are task
            priorities under the same cluster
        """
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

        NOTE: the priority values is given in the range of [0, len(cluster_order)],
            priority 0 is given to the papers that are not part of any clsuters

        Args:
            cluster_order: an ordered list of clusterIds where lower index has higher priority.
            question_idx: question_index of the clustering context.
            version: version of the clustering context.


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
        """Get a dict mapping clusterId to list of papers under a q,v contenxt.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        """
        clusters = QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            type=ClusteringGroupType.user_facing,
        ).prefetch_related("paper")

        return {cluster.clusterId: list(cluster.paper.all()) for cluster in clusters}

    @transaction.atomic
    def bulk_tagging(self, question_idx: int, version: int, userid: int):
        """Bulk tag all clusters with default cluster tag.

        NOTE: current default cluster tag is cluster_{question_idx}_{version}_{clusterId}.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            userid: the id of the user who calls the tagging.

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
        """Remove a tag identified with tag_pk from all tasks in the cluster.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterId: identifier of the cluster.
            tag_pk: the primary key of the tag to be removed from the cluster.
        """
        # Get all tasks in the cluster
        tasks = self.get_all_tasks_in_a_cluster(question_idx, version, clusterId)

        # get all relevant MarkingTaskTag
        task_tags = MarkingTaskTag.objects.filter(task__in=tasks, id=tag_pk)

        task_tags.delete()

    def _get_cluster_id_from_cluster_tag(self, cluster_tag_text: str) -> int:
        """Get the cluster id given a cluster tag.

        Args:
            cluster_tag_text: the text of the cluster tag, currently following the format
                of clsuter_{question_index}_{version}_{clusterId}.

        Returns:
            the clusterId parsed from the cluster tag text.
        """
        return int(cluster_tag_text.rsplit("_", 1)[-1])

    def get_all_tasks_in_a_cluster(
        self, question_idx: int, version: int, clusterId: int
    ) -> QuerySet[MarkingTask]:
        """Get all tasks in a cluster.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterId: the identifier of the cluster.

        Returns:
            QuerySet of all MarkingTask in the queried cluster.
        """
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
        """Return a mapping from clusterId to a set of tags in the cluster.

        NOTE: The tags that are included in the set are those that are shared across all tasks
            within the cluster.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A mapping from clusterId to a set of tags shared across all tasks in the cluster.
            Each tag is represented as (tag.pk, tag.text).
        """
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
        cluster_to_common_tag = {}

        for cid, papers in cluster_to_papers.items():
            # Get all tasks for this cluster (via its papers)
            task_list = []
            for p in papers:
                task_list.extend(paper_to_tasks.get(p.id, []))

            if not task_list:
                cluster_to_common_tag[cid] = []
                continue

            # Start with tags from first task, then intersect
            common = {(tg.pk, tg.text) for tg in task_list[0].markingtasktag_set.all()}
            for t in task_list[1:]:
                common = common.intersection(
                    {(tg.pk, tg.text) for tg in t.markingtasktag_set.all()}
                )  # set intersection

            cluster_to_common_tag[cid] = common

        return cluster_to_common_tag

    def get_corners_used_for_clustering(
        self, question_idx: int, version: int
    ) -> dict[str, float]:
        """Get the rectangle used for clustering in a (q, v) context.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A dict representing the rectangular region and has these
            keys: [top, left, bottom, right].
        """
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

    def get_merged_component_count(
        self, question_idx: int, version: int
    ) -> dict[int, int]:
        """Get a mapping from clusterId to the count of count of merged components.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.

        Returns:
            A dict mapping clusterId to count of merged clusters.
        """
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

    @transaction.atomic
    def merge_clusters(
        self, question_idx: int, version: int, clusterIds: list[int]
    ) -> int:
        """Merge all clusters in clusterIDs within a (q, v) context.

        NOTE: the resulting cluster is the cluster of minimum ID.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterIds: the identifier of the clusters to be merged.

        Returns:
            Cluster id of the merged clusters.

        Raises:
            EmptySelectedError: if attempting to merge 0 cluster
        """
        if len(clusterIds) == 0:
            raise EmptySelectedError("attempting to merge empty clusters")

        # Check if clusters have conflicting tags:
        cluster_to_tags = self.cluster_ids_to_tags(question_idx, version)

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
        return target_cluster_id

    @transaction.atomic
    def delete_clusters(
        self, question_idx: int, version: int, clusterIds: list[int]
    ) -> None:
        """Delete clusters in clusterIds in a (q, v) context.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterIds: the identifier of the clusters to be deleted.

        Raises:
            EmptySelectedError: if attempts to delete 0 cluster.
        """
        if len(clusterIds) == 0:
            raise EmptySelectedError("attempting to delete 0 cluster")
        QVCluster.objects.filter(
            question_idx=question_idx,
            version=version,
            clusterId__in=set(clusterIds),
            type=ClusteringGroupType.user_facing,
        ).delete()

    @transaction.atomic
    def delete_cluster_member(
        self, question_idx: int, version: int, clusterId: int, paper_num: int
    ) -> int:
        """Remove a paper from a cluster.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
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
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )
        qvc.paper.remove(paper)

        member_count = len(qvc.paper.all())

        return member_count

    @transaction.atomic
    def bulk_delete_cluster_members(
        self, question_idx: int, version: int, clusterId: int, paper_nums: list[int]
    ) -> int:
        """Bulk remove paper_nums from a cluster.

        NOTE: this function is optimized to avoid N+1 queries, such that it avoids
            calling delete_cluster_member.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
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
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            type=ClusteringGroupType.user_facing,
        )

        qvc.paper.remove(*papers_to_remove)

        member_count = len(qvc.paper.all())

        return member_count

    def reset_clusters(
        self, question_idx: int, version: int, clusterIds: list[int]
    ) -> None:
        """Reset all cluster in clusterIds to their original state.

        NOTE: This also resets the state of the papers in the clusters and cluster tag.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterIds: the list of Ids of clusters to be reset.

        Raises:
            EmptySelectedError: attempts to reset 0 cluster.
        """
        if not clusterIds:
            raise EmptySelectedError("attempting to reset 0 cluster.")

        for cid in clusterIds:
            self._reset_cluster(question_idx, version, cid)

    def _reset_cluster(self, question_idx: int, version: int, clusterId: int) -> None:
        """Reset the cluster identified by the (q, v, clusterId).

        NOTE: This also resets the state of the papers in the cluster and remove cluster tag.

        Args:
            question_idx: question_index of the clustering context.
            version: version of the clustering context.
            clusterId: the identifier of the cluster to be reset.
        """
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
    """Build a cluster mapping for a single question, version pair.

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
    qcs.cluster_qv(question_idx, version, page_num, rect, clustering_model)

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
