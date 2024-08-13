# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.urls import path

from .views import (
    ProgressIdentifyHome,
    ProgressMarkHome,
    ProgressMarkStatsView,
    ProgressMarkDetailsView,
    ProgressMarkVersionCompareView,
    ProgressMarkingTaskFilterView,
    ProgressMarkingTaskDetailsView,
    ProgressNewestMarkingTaskDetailsView,
    AnnotationImageWrapView,
    AnnotationImageView,
    MarkingTaskTagView,
    MarkingTaskResetView,
    MarkingTaskReassignView,
    OriginalImageWrapView,
    ProgressUserInfoHome,
    AllTaskOverviewView,
    OverviewLandingView,
    IDImageView,
    ClearID,
    IDImageWrapView,
)

urlpatterns = [
    path(
        "mark/overview/",
        ProgressMarkHome.as_view(),
        name="progress_mark_home",
    ),
    path(
        "mark/stats/<int:question>/<int:version>",
        ProgressMarkStatsView.as_view(),
        name="progress_mark_stats",
    ),
    path(
        "mark/details/<int:question>/<int:version>",
        ProgressMarkDetailsView.as_view(),
        name="progress_mark_details",
    ),
    path(
        "mark/task_filter/",
        ProgressMarkingTaskFilterView.as_view(),
        name="progress_marking_task_filter",
    ),
    path(
        "mark/task_details/<int:task_pk>",
        ProgressMarkingTaskDetailsView.as_view(),
        name="progress_marking_task_details",
    ),
    path(
        "mark/newest_task_details/<int:task_pk>",
        ProgressNewestMarkingTaskDetailsView.as_view(),
        name="progress_newest_marking_task_details",
    ),
    path(
        "mark/task_annotation/annotation_img_wrap/<int:paper>/<int:question>",
        AnnotationImageWrapView.as_view(),
        name="progress_annotation_img_wrap",
    ),
    path(
        "mark/task_annotation/annotation_img/<int:paper>/<int:question>",
        AnnotationImageView.as_view(),
        name="progress_annotation_img",
    ),
    path(
        "mark/task_annotation/original_img_wrap/<int:paper>/<int:question>",
        OriginalImageWrapView.as_view(),
        name="progress_original_img_wrap",
    ),
    path(
        "mark/compare/<int:question>",
        ProgressMarkVersionCompareView.as_view(),
        name="progress_mark_version_compare",
    ),
    path(
        "identify/overview/",
        ProgressIdentifyHome.as_view(),
        name="progress_identify_home",
    ),
    path(
        "identify/overview/id_img/<int:image_pk>",
        IDImageView.as_view(),
        name="ID_img",
    ),
    path(
        "identify/overview/id_img/clear/<int:paper_number>",
        ClearID.as_view(),
        name="clear_ID",
    ),
    path(
        "identify/overview/id_img_wrap/<int:image_pk>",
        IDImageWrapView.as_view(),
        name="ID_img_wrap",
    ),
    path(
        "userinfo/overview/",
        ProgressUserInfoHome.as_view(),
        name="progress_user_info_home",
    ),
    path(
        "all_task_overview/",
        AllTaskOverviewView.as_view(),
        name="all_task_overview",
    ),
    path(
        "overview_landing/",
        OverviewLandingView.as_view(),
        name="overview_landing",
    ),
    path(
        "task_tag/<int:task_pk>/<int:tag_pk>",
        MarkingTaskTagView.as_view(),
        name="marking_task_tag",
    ),
    path(
        "new_task_tag/<int:task_pk>",
        MarkingTaskTagView.as_view(),
        name="create_marking_task_tag",
    ),
    path(
        "mark/reset_task/<int:task_pk>",
        MarkingTaskResetView.as_view(),
        name="reset_marking_task",
    ),
    path(
        "mark/reassign_task/<int:task_pk>",
        MarkingTaskReassignView.as_view(),
        name="reassign_marking_task",
    ),
]
