# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.urls import path
from .views import (
    PreparationLandingView,
    PreparationDependencyConflictView,
    LandingResetSources,
    LandingPrenameToggle,
    LandingResetClasslist,
    LandingResetQVmap,
    LandingFinishedToggle,
    SourceManageView,
    SourceReadOnlyView,
    PrenamingView,
    ClasslistView,
    ClasslistDownloadView,
    ClasslistReadOnlyView,
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
    MockExamView,
    PaperCreationView,
    MiscExtrasView,
    ExtraPageView,
    ScrapPaperView,
    ReferenceImageView,
)

urlpatterns = [
    path("", PreparationLandingView.as_view(), name="prep_landing"),
    path("conflict", PreparationDependencyConflictView.as_view(), name="prep_conflict"),
    path("reset/sources/", LandingResetSources.as_view(), name="prep_reset_sources"),
    path(
        "reset/prenaming/", LandingPrenameToggle.as_view(), name="prep_prename_toggle"
    ),
    path(
        "reset/classlist/", LandingResetClasslist.as_view(), name="prep_reset_classlist"
    ),
    path("reset/qvmap/", LandingResetQVmap.as_view(), name="prep_reset_qvmap"),
    path("source/", SourceManageView.as_view(), name="prep_sources"),
    path(
        "source/<int:version>",
        SourceManageView.as_view(),
        name="prep_source_upload",
    ),
    path("source/mock/<int:version>", MockExamView.as_view(), name="prep_mock"),
    path("source/view/", SourceReadOnlyView.as_view(), name="prep_source_view"),
    path("prename/", PrenamingView.as_view(), name="prep_prename"),
    path("classlist/", ClasslistView.as_view(), name="prep_classlist"),
    path(
        "classlist/download",
        ClasslistDownloadView.as_view(),
        name="prep_classlist_download",
    ),
    path(
        "classlist/view/", ClasslistReadOnlyView.as_view(), name="prep_classlist_view"
    ),
    path("qvmapping/", PQVMappingView.as_view(), name="prep_qvmapping"),
    path(
        "qvmapping/download",
        PQVMappingDownloadView.as_view(),
        name="prep_qvmapping_download",
    ),
    path(
        "qvmapping/delete", PQVMappingDeleteView.as_view(), name="prep_qvmapping_delete"
    ),
    path(
        "qvmapping/upload", PQVMappingUploadView.as_view(), name="prep_qvmapping_upload"
    ),
    path("test_papers/", PaperCreationView.as_view(), name="prep_test_papers"),
    path("misc/", MiscExtrasView.as_view(), name="misc_extras"),
    path("misc/extra_page", ExtraPageView.as_view(), name="extra_page"),
    path("misc/scrap_paper", ScrapPaperView.as_view(), name="scrap_paper"),
    path(
        "pref_finished/", LandingFinishedToggle.as_view(), name="prep_finished_toggle"
    ),
    path(
        "reference_image/<int:version>/<int:page>",
        ReferenceImageView.as_view(),
        name="reference_image",
    ),
]
