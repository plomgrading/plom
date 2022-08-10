from django.urls import path
from .views import PreparationLandingView, TestSourceManageView, PrenamingView, ClasslistView, ClasslistDownloadView, ClasslistDeleteView, PQVMappingView

urlpatterns = [
    path("", PreparationLandingView.as_view()),
    path("test_source/", TestSourceManageView.as_view()),
    path("test_source/<int:version>", TestSourceManageView.as_view()),
    path("prename/", PrenamingView.as_view()),
    path("classlist/", ClasslistView.as_view()),
    path("classlist/download", ClasslistDownloadView.as_view()),
    path("classlist/delete", ClasslistDeleteView.as_view()),
    path("qvmapping/", PQVMappingView.as_view()),
]
