from django.urls import path
from .views import ClasslistView, ClasslistWholeView

urlpatterns = [
    path('', ClasslistView.as_view()),
    path("everyone", ClasslistWholeView.as_view()),
]
