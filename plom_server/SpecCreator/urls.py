# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path

from . import views


# TODO: Document the API here? Sphinx best practices?

urlpatterns = [
    path("", views.TestSpecLaunchView.as_view(), name="creator_launch"),
    path("names/", views.TestSpecCreatorNamesPage.as_view(), name="names"),
    path("upload", views.TestSpecCreatorVersionsRefPDFPage.as_view(), name="upload"),
    path("upload/view/", views.TestSpecViewRefPDF.as_view(), name="ref_pdf_view"),
    path("id_page/", views.TestSpecCreatorIDPage.as_view(), name="id_page"),
    path("questions/", views.TestSpecCreatorQuestionsPage.as_view(), name="questions"),
    path(
        "questions/<int:q_idx>",
        views.TestSpecCreatorQuestionDetailPage.as_view(),
        name="q_detail",
    ),
    path("dnm_pages/", views.TestSpecCreatorDNMPage.as_view(), name="dnm_page"),
    path("validate/", views.TestSpecValidateView.as_view(), name="validate"),
    path("submit/", views.TestSpecSubmitView.as_view(), name="spec_submit"),
    path("download/", views.TestSpecDownloadView.as_view(), name="download"),
    path("summary", views.TestSpecSummaryView.as_view(), name="spec_summary"),
    path("reset/", views.TestSpecResetView.as_view(), name="reset_spec"),
    path(
        "reset/landing/",
        views.TestSpecPrepLandingResetView.as_view(),
        name="reset_spec_landing",
    ),
    path("gen_spec/", views.TestSpecGenTomlView.as_view(), name="generate_spec"),
]
