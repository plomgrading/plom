# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2025 Aidan Murphy

from django.urls import path

from . import views


urlpatterns = [
    path("users", view=views.UserPage.as_view(), name="users"),
    path("users/<str:username>", views.UserPage.as_view(), name="modify_user"),
    path(
        "user_reset/<str:username>",
        views.PasswordResetPage.as_view(),
        name="reset_user_password",
    ),
    # path("users/refresh/", views.UserPage.retryConnection, name="retry_user_page"),
    path("disableScanners/", views.UserPage.disableScanners, name="disableScanners"),
    path("enableScanners/", views.UserPage.enableScanners, name="enableScanners"),
    path("disableMarkers/", views.UserPage.disableMarkers, name="disableMarkers"),
    path("enableMarkers/", views.UserPage.enableMarkers, name="enableMarkers"),
    path(
        "toggleLeadMarker/<str:username>",
        views.UserToggleLeadMarker.as_view(),
        name="toggleLeadMarker",
    ),
    path("explosion", views.HTMXExplodeView.as_view(), name="htmx_explode"),
    path(
        "set_quota/<str:username>/",
        views.SetQuotaView.as_view(),
        name="set_quota",
    ),
    path(
        "unset_quota/<str:username>/",
        views.UnsetQuotaView.as_view(),
        name="unset_quota",
    ),
    path(
        "bulk_set_quota/",
        views.BulkSetQuotaView.as_view(),
        name="bulk_set_quota",
    ),
    path(
        "bulk_unset_quota/",
        views.BulkUnsetQuotaView.as_view(),
        name="bulk_unset_quota",
    ),
]
