# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.urls import path
from .views import TroublesAfootGenericErrorView


urlpatterns = [
    path(
        "troubles_afoot/<str:hint>",
        TroublesAfootGenericErrorView.as_view(),
        name="troubles_afoot",
    ),
]
