# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2026 Deep Shah

from django.urls import path

from .views import (
    QuestionClusteringHomeView,
    SelectRectangleForClusteringView,
    DetectMCQBoxesView,
    PreviewSelectedRectsView,
    QuestionClusteringJobsHome,
    QuestionClusteringJobTable,
    ClusterGroupsView,
    UnclusteredPapersView,
    ClusteredPapersView,
    DeleteClusterMember,
    ClusterMergeView,
    ClusterBulkDeleteView,
    AssignUnclusteredPapersView,
    CreateClusterFromUnclusteredPapersView,
    SuggestUnclusteredPapersView,
    ClusterResetView,
    UpdateClusterPriorityView,
    UpdateClusterNameView,
    ClusterBulkTaggingView,
    RemoveTagFromClusterView,
    ClusteringErrorJobInfoView,
    RemoveJobView,
    Debug,
)

urlpatterns = [
    # ====== Clustering Home Page (choose q, v, page) ========
    path("", QuestionClusteringHomeView.as_view(), name="question_clustering_home"),
    # ========== Rectangle selector for clustering ===========
    path(
        "select/<int:version>/<int:qidx>/<int:page>",
        SelectRectangleForClusteringView.as_view(),
        name="question_clustering_select_rectangle",
    ),
    path(
        "detect_mcq_boxes/<int:version>/<int:page>",
        DetectMCQBoxesView.as_view(),
        name="question_clustering_detect_mcq_boxes",
    ),
    # ======== Page to preview selected regions ===============
    path(
        "clustering_region_preview",
        PreviewSelectedRectsView.as_view(),
        name="preview_clustering_region",
    ),
    # ========= List of clustering jobs page (table of jobs) =================
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
        "cluster_error_job_info/<int:task_id>",
        ClusteringErrorJobInfoView.as_view(),
        name="cluster_error_job_info",
    ),
    path(
        "remove_clustering_job/<int:task_id>",
        RemoveJobView.as_view(),
        name="remove_clustering_job",
    ),
    # === Cluster detail page (# members, priorities, tags, etc) =========
    path(
        "cluster_groups/<int:task_id>",
        ClusterGroupsView.as_view(),
        name="cluster_groups",
    ),
    path(
        "cluster_groups/<int:task_id>/unclustered",
        UnclusteredPapersView.as_view(),
        name="unclustered_papers",
    ),
    # ======= Clustering-group operation in clustering table page =======
    path("merge_clusters/", ClusterMergeView.as_view(), name="merge_clusters"),
    path(
        "bulk_delete_clusters/",
        ClusterBulkDeleteView.as_view(),
        name="bulk_delete_clusters",
    ),
    path(
        "assign_unclustered_papers/",
        AssignUnclusteredPapersView.as_view(),
        name="assign_unclustered_papers",
    ),
    path(
        "create_cluster_from_unclustered_papers/",
        CreateClusterFromUnclusteredPapersView.as_view(),
        name="create_cluster_from_unclustered_papers",
    ),
    path(
        "suggest_unclustered_papers/",
        SuggestUnclusteredPapersView.as_view(),
        name="suggest_unclustered_papers",
    ),
    path(
        "reset_clusters/",
        ClusterResetView.as_view(),
        name="reset_clusters",
    ),
    path(
        "delete_cluster_member",
        DeleteClusterMember.as_view(),
        name="delete_cluster_member",
    ),
    # ======= Clustering utilities in clustering table page =======
    path(
        "update_cluster_priority/",
        UpdateClusterPriorityView.as_view(),
        name="update_cluster_priority",
    ),
    path(
        "update_cluster_name/",
        UpdateClusterNameView.as_view(),
        name="update_cluster_name",
    ),
    path(
        "bulk_cluster_tagging/",
        ClusterBulkTaggingView.as_view(),
        name="bulk_cluster_tagging",
    ),
    # =========== Papers inside a cluster ==============
    path(
        "remove_tag_from_cluster",
        RemoveTagFromClusterView.as_view(),
        name="remove_tag_from_cluster",
    ),
    path(
        "clustered_papers/<int:task_id>/<int:clusterId>",
        ClusteredPapersView.as_view(),
        name="clustered_papers",
    ),
    path("remove-huey-debug/", Debug.as_view(), name="remove_huey_debug"),
]
