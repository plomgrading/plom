# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.urls import path
from .views import TroublesAfootGenericErrorView
from .views import ServerStatusView, ResetView


urlpatterns = [
    path(
        "troubles_afoot/<str:hint>",
        TroublesAfootGenericErrorView.as_view(),
        name="troubles_afoot",
    ),
    path("reset/", ResetView.as_view(), name="reset"),
    path("server_status", ServerStatusView.as_view(), name="server_status"),
]
