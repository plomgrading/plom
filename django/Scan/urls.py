# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.urls import path

from Scan.views import (
    ScannerHomeView,
    ManageBundleView,
    GetBundleView,
    GetBundleImageView,
    RemoveBundleView,
    ReadQRcodesView,
)


urlpatterns = [
    path("", ScannerHomeView.as_view(), name="scan_home"),
    path(
        "<str:slug>/<timestamp>/", ManageBundleView.as_view(), name="scan_manage_bundle"
    ),
    path(
        "bundle/<str:slug>/<timestamp>/",
        GetBundleView.as_view(),
        name="scan_get_bundle",
    ),
    path(
        "bundle/<str:slug>/<timestamp>/<int:index>/",
        GetBundleImageView.as_view(),
        name="scan_get_image",
    ),
    path(
        "delete/<str:slug>/<timestamp>/",
        RemoveBundleView.as_view(),
        name="scan_remove_bundle",
    ),
    path(
        "read/<str:slug>/<timestamp>",
        ReadQRcodesView.as_view(),
        name="scan_read_qr",
    ),
]
