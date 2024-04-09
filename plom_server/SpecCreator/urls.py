# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from django.urls import path

from . import views


urlpatterns = [
    path("", views.SpecEditorView.as_view(), name="creator_launch"),
    path("download", views.SpecDownloadView.as_view(), name="spec_download"),
    path("upload", views.SpecUploadView.as_view(), name="spec_upload"),
    path("summary", views.SpecSummaryView.as_view(), name="spec_summary"),
    path(
        "summary/<int:question_number>",
        views.HTMXSummaryQuestion.as_view(),
        name="spec_summary_q",
    ),
    path(
        "template",
        views.TemplateSpecBuilderView.as_view(),
        name="template_spec_builder",
    ),
]
