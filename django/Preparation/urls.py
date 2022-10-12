# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates

from django.urls import path
from .views import (
    PreparationLandingView,
    LandingResetSpec,
    LandingResetSources,
    LandingPrenameToggle,
    LandingResetClasslist,
    LandingResetQVmap,
    TestSourceManageView,
    PrenamingView,
    ClasslistView,
    ClasslistDownloadView,
    ClasslistDeleteView,
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
    PQVMappingReadOnlyView,
    ClassicServerInfoView,
    ClassicServerURLView,
    MockExamView,
    PaperCreationView,
)

urlpatterns = [
    path("", PreparationLandingView.as_view(), name="prep_landing"),
    path("reset/spec/", LandingResetSpec.as_view(), name="prep_reset_spec"),
    path("reset/sources/", LandingResetSources.as_view(), name="prep_reset_sources"),
    path(
        "reset/prenaming/", LandingPrenameToggle.as_view(), name="prep_prename_toggle"
    ),
    path(
        "reset/classlist/", LandingResetClasslist.as_view(), name="prep_reset_classlist"
    ),
    path("reset/qvmap/", LandingResetQVmap.as_view(), name="prep_reset_qvmap"),
    path("test_source/", TestSourceManageView.as_view(), name="prep_sources"),
    path(
        "test_source/<int:version>",
        TestSourceManageView.as_view(),
        name="prep_source_upload",
    ),
    path("test_source/mock/<int:version>", MockExamView.as_view(), name="prep_mock"),
    path("prename/", PrenamingView.as_view(), name="prep_prename"),
    path("classlist/", ClasslistView.as_view(), name="prep_classlist"),
    path(
        "classlist/download",
        ClasslistDownloadView.as_view(),
        name="prep_classlist_download",
    ),
    path(
        "classlist/delete", ClasslistDeleteView.as_view(), name="prep_classlist_delete"
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
    path("qvmapping/view/", PQVMappingReadOnlyView.as_view(), name="prep_qvmapping_view"),
    path("classic/", ClassicServerInfoView.as_view(), name="prep_server_info"),
    path("classic/server", ClassicServerURLView.as_view(), name="prep_server"),
    path("test_papers/", PaperCreationView.as_view(), name="prep_test_papers"),
]
