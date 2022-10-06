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
        "<timestamp>/", ManageBundleView.as_view(), name="scan_manage_bundle"
    ),
    path(
        "bundle/<timestamp>/",
        GetBundleView.as_view(),
        name="scan_get_bundle",
    ),
    path(
        "bundle/<timestamp>/<int:index>/",
        GetBundleImageView.as_view(),
        name="scan_get_image",
    ),
    path(
        "delete/<timestamp>/",
        RemoveBundleView.as_view(),
        name="scan_remove_bundle",
    ),
    path(
        "read/<timestamp>",
        ReadQRcodesView.as_view(),
        name="scan_read_qr",
    ),
]
