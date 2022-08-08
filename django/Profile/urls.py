from django.urls import path

import Profile.views

urlpatterns = [
    path('profile/', Profile.views.Profile.as_view(), name='profile'),
]
