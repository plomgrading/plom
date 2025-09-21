# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.urls import path
from .views import (
    PublicCodeView,
    PreparationLandingView,
    PreparationDependencyConflictView,
    PreparationFinishedView,
    SourceManageView,
    PrenamingConfigView,
    PrenamingView,
    ClasslistView,
    ClasslistDownloadView,
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
    MiscellaneaView,
    MiscellaneaDownloadExtraPageView,
    MiscellaneaDownloadScrapPaperView,
    MiscellaneaDownloadBundleSeparatorView,
    MockExamView,
    ReferenceImageView,
)

urlpatterns = [
    path("", PreparationLandingView.as_view(), name="prep_landing"),
    path("conflict", PreparationDependencyConflictView.as_view(), name="prep_conflict"),
    path("source/", SourceManageView.as_view(), name="prep_sources"),
    path(
        "source/<int:version>",
        SourceManageView.as_view(),
        name="prep_source_upload",
    ),
    path("source/mock/<int:version>", MockExamView.as_view(), name="prep_mock"),
    path("prename/", PrenamingView.as_view(), name="prep_prename"),
    path(
        "prename/configure", PrenamingConfigView.as_view(), name="configure_prenaming"
    ),
    path("classlist/", ClasslistView.as_view(), name="prep_classlist"),
    path(
        "classlist/download",
        ClasslistDownloadView.as_view(),
        name="prep_classlist_download",
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
    path("misc/", MiscellaneaView.as_view(), name="miscellanea"),
    path(
        "misc/extra_page.pdf",
        MiscellaneaDownloadExtraPageView.as_view(),
        name="miscellanea_extra_page.pdf",
    ),
    path(
        "misc/scrap_paper.pdf",
        MiscellaneaDownloadScrapPaperView.as_view(),
        name="miscellanea_scrap_paper.pdf",
    ),
    path(
        "misc/bundle_separator_paper.pdf",
        MiscellaneaDownloadBundleSeparatorView.as_view(),
        name="miscellanea_bundle_separator.pdf",
    ),
    path(
        "prep_finished/",
        PreparationFinishedView.as_view(),
        name="prep_finished",
    ),
    path(
        "reference_image/<int:version>/<int:page>",
        ReferenceImageView.as_view(),
        name="reference_image",
    ),
    path(
        "public_code/",
        PublicCodeView.as_view(),
        name="public_code",
    ),
]
