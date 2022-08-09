from django.urls import path
from .views import ClasslistView, ClasslistDownloadView, ClasslistDeleteEverythingView

urlpatterns = [
    path("", ClasslistView.as_view()),
    path("download", ClasslistDownloadView.as_view()),
    path("delete", ClasslistDeleteEverythingView.as_view()),
]
