# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.urls import path

import Profile.views

urlpatterns = [
    path("profile/", Profile.views.Profile.as_view(), name="profile"),
]
