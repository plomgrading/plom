from django.urls import path
from .views import PreparationLandingView

urlpatterns = [
    path("", PreparationLandingView.as_view()),
]
