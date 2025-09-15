# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Bryan Tanady

from django.urls import path

from . import views


urlpatterns = [
    path("", views.RubricLandingPageView.as_view(), name="rubrics_landing"),
    path("admin/", views.RubricAdminPageView.as_view(), name="rubrics_admin"),
    path("admin/half/", views.RubricCreateHalfMarksView.as_view(), name="rubric_half"),
    path(
        "admin/pref/",
        views.RubricFractionalPreferencesView.as_view(),
        name="rubric_fractional_pref",
    ),
    path("admin/access/", views.RubricAccessPageView.as_view(), name="rubrics_access"),
    path(
        "admin/feedback_rules/",
        views.FeedbackRulesView.as_view(),
        name="feedback_rules",
    ),
    path("admin/download/", views.DownloadRubricView.as_view(), name="rubric_download"),
    path(
        "admin/download_rubric_template/",
        views.DownloadRubricTemplateView.as_view(),
        name="rubric_template_download",
    ),
    path("admin/upload/", views.UploadRubricView.as_view(), name="rubric_upload"),
    path("<int:rid>/", views.RubricItemView.as_view(), name="rubric_item"),
    path(
        "<int:rid>/compare", views.RubricsCompareView.as_view(), name="compare_rubrics"
    ),
    path("<int:rid>/edit/", views.RubricEditView.as_view(), name="rubric_edit"),
    path("create", views.RubricCreateView.as_view(), name="rubric_create"),
]
