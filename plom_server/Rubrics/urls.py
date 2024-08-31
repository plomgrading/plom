# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.urls import path

from . import views


urlpatterns = [
    path("", views.RubricLandingPageView.as_view(), name="rubrics_landing"),
    path("admin/", views.RubricAdminPageView.as_view(), name="rubrics_admin"),
    path("admin/demo/", views.RubricDemoView.as_view(), name="rubric_demo"),
    path("admin/wipe/", views.RubricWipePageView.as_view(), name="rubrics_wipe"),
    path("admin/access/", views.RubricAccessPageView.as_view(), name="rubrics_access"),
    path(
        "admin/feedback_rules/",
        views.FeedbackRulesView.as_view(),
        name="feedback_rules",
    ),
    path("<int:rid>/", views.RubricItemView.as_view(), name="rubric_item"),
    path("admin/download/", views.DownloadRubricView.as_view(), name="rubric_download"),
    path("admin/upload/", views.UploadRubricView.as_view(), name="rubric_upload"),
    path("<int:rid>/compare", views.compare_rubrics, name="compare_rubrics"),
    path("rubrics/create", views.RubricCreateView.as_view(), name="rubric_create"),
    path("<int:rid>/edit/", views.RubricEditView.as_view(), name="rubric_edit"),
]
