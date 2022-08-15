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
    ClassicServerURLView
)

urlpatterns = [
    path("", PreparationLandingView.as_view(), name="prep_landing"),
    path("test_source/", TestSourceManageView.as_view(), name="prep_sources"),
    path("test_source/<int:version>", TestSourceManageView.as_view(), name="prep_source_upload"),
    path("prename/", PrenamingView.as_view(), name='prep_prename'),
    path("classlist/", ClasslistView.as_view()),
    path("classlist/download", ClasslistDownloadView.as_view()),
    path("classlist/delete", ClasslistDeleteView.as_view()),
    path("qvmapping/", PQVMappingView.as_view()),
    path("qvmapping/download", PQVMappingDownloadView.as_view()),
    path("qvmapping/delete", PQVMappingDeleteView.as_view()),
    path("qvmapping/upload", PQVMappingUploadView.as_view()),
    path("classic/", ClassicServerInfoView.as_view()),
    path("classic/server", ClassicServerURLView.as_view()),
]
