# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from django.urls import path

from .views import (
    QuestionClusteringHomeView,
    SelectRectangleForClusteringView,
    PreviewSelectedRectsView,
    QuestionClusteringJobsHome,
    QuestionClusteringJobTable,
    ClusterGroupsView,
    ClusteredPapersView,
    DeleteClusterMember,
    ClusterMergeView,
    ClusterBulkDeleteView,
    ClusterBulkResetView,
    UpdateClusterPriorityView,
    ClusterBulkTaggingView,
    RemoveTagFromClusterView,
    ClusteringErrorJobInfoView,
    Debug,
)


urlpatterns = [
    # ======= Question Clustering Page URLs =======
    path("", QuestionClusteringHomeView.as_view(), name="question_clustering_home"),
    path(
        "select/<int:version>/<int:qidx>/<int:page>",
        SelectRectangleForClusteringView.as_view(),
        name="question_clustering_select_rectangle",
    ),
    path(
        "clustering_region_preview",
        PreviewSelectedRectsView.as_view(),
        name="preview_clustering_region",
    ),
    path(
        "question_clustering_jobs_home",
        QuestionClusteringJobsHome.as_view(),
        name="question_clustering_jobs_home",
    ),
    path(
        "question_clustering_jobs",
        QuestionClusteringJobTable.as_view(),
        name="get_question_clustering_tasks",
    ),
    path(
        "cluster_groups/<int:question_idx>/<int:version>/<int:page_num>",
        ClusterGroupsView.as_view(),
        name="cluster_groups",
    ),
    path(
        "clustered_papers/<int:question_idx>/<int:version>/<int:page_num>/<int:clusterId>",
        ClusteredPapersView.as_view(),
        name="clustered_papers",
    ),
    path(
        "cluster_error_job_info/<int:task_id>",
        ClusteringErrorJobInfoView.as_view(),
        name="cluster_error_job_info",
    ),
    # ======= Clustering-cleanup  =======
    path("merge_clusters/", ClusterMergeView.as_view(), name="merge_clusters"),
    path(
        "bulk_delete_clusters/",
        ClusterBulkDeleteView.as_view(),
        name="bulk_delete_clusters",
    ),
    path(
        "bulk_reset_clusters/",
        ClusterBulkResetView.as_view(),
        name="bulk_reset_clusters",
    ),
    path(
        "delete_cluster_member/<int:question_idx>/<int:version>/<int:page_num>/<int:clusterId>",
        DeleteClusterMember.as_view(),
        name="delete_cluster_member",
    ),
    # ======= Post-clustering-cleanup utilis =======
    path(
        "update_cluster_priority/",
        UpdateClusterPriorityView.as_view(),
        name="update_cluster_priority",
    ),
    path(
        "bulk_cluster_tagging/",
        ClusterBulkTaggingView.as_view(),
        name="bulk_cluster_tagging",
    ),
    # ======= Misc clustering features =======
    path(
        "remove_tag_from_cluster",
        RemoveTagFromClusterView.as_view(),
        name="remove_tag_from_cluster",
    ),
    path("remove-huey-debug/", Debug.as_view(), name="remove_huey_debug"),
]
