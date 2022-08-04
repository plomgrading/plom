from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClasslistView.as_view())
]
