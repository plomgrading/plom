from django.urls import path
from .views import PreparationLandingView, TestSourceManageView, PrenamingView

urlpatterns = [
    path("", PreparationLandingView.as_view()),
    path("test_source/", TestSourceManageView.as_view()),
    path("test_source/<int:version>", TestSourceManageView.as_view()),
    path("prename/", PrenamingView.as_view())
]
