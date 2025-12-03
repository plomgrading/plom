# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Aidan Murphy

from django.urls import path

from .views import ProfileView, PrivateProfileView, password_change_redirect

urlpatterns = [
    path("profile/<str:username>", ProfileView.as_view(), name="profile"),
    path("profile/", PrivateProfileView.as_view(), name="private_profile"),
    path(
        "profile/password",
        password_change_redirect,
        name="self-password-reset",
    ),
]
