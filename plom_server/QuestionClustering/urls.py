# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from django.urls import path

from .views import (
    QuestionClusteringHomeView,
    SelectRectangleForClusteringView,
    QuestionClusteringJobsHome,
    GetQuestionClusteringJobs,
    ClusterGroupsView,
    ClusteredPapersView,
    DeleteClusterMember,
    Debug,
)


urlpatterns = [
    path("", QuestionClusteringHomeView.as_view(), name="question_clustering_home"),
    path(
        "select/<int:version>/<int:qidx>/<int:page>",
        SelectRectangleForClusteringView.as_view(),
        name="question_clustering_select_rectangle",
    ),
    path(
        "question_clustering_jobs_home",
        QuestionClusteringJobsHome.as_view(),
        name="question_clustering_jobs_home",
    ),
    path(
        "question_clustering_jobs",
        GetQuestionClusteringJobs.as_view(),
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
        "delete_cluster_member/<int:question_idx>/<int:version>/<int:page_num>/<int:clusterId>",
        DeleteClusterMember.as_view(),
        name="delete_cluster_member",
    ),
    path("remove-huey-debug/", Debug.as_view(), name="remove_huey_debug"),
]
