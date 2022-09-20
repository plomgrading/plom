from django.urls import path
from .views import (
    PreparationLandingView,
    TestSourceManageView,
    PrenamingView,
    ClasslistView,
    ClasslistDownloadView,
    ClasslistDeleteView,
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
    ClassicServerInfoView,
    ClassicServerURLView,
    MockExamView,
    PaperCreationView,
)

urlpatterns = [
    path("", PreparationLandingView.as_view(), name="prep_landing"),
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
    path("classic/", ClassicServerInfoView.as_view(), name="prep_server_info"),
    path("classic/server", ClassicServerURLView.as_view(), name="prep_server"),
    path("test_papers/", PaperCreationView.as_view(), name="prep_test_papers"),
]
