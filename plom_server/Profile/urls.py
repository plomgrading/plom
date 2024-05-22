# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path

import Profile.views

urlpatterns = [
    path("profile/", Profile.views.Profile.as_view(), name="profile"),
    path(
        "profile/password",
        Profile.views.password_change_redirect,
        name="self-password-reset",
    ),
]
