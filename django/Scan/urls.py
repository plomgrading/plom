# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from django.urls import path

from Scan.views import (
    ScannerHomeView,
    BundleSplittingProgressView,
    BundleSplittingUpdateView,
    ManageBundleView,
    UpdateQRProgressView,
    GetBundleView,
    GetBundleImageView,
    RemoveBundleView,
    ReadQRcodesView,
    QRParsingProgressAlert,
    BundleTableView,
    PushPageImage,
    PushAllPageImages,
    PagePushingUpdateView,
    FlagPageImage,
    ScannerSummaryView,
    ChangeErrorImageState,
    ReplacePageImage,
)


urlpatterns = [
    path("", ScannerHomeView.as_view(), name="scan_home"),
    path(
        "<timestamp>/<int:index>/",
        ManageBundleView.as_view(),
        name="scan_manage_bundle",
    ),
    path(
        "split/<timestamp>/",
        BundleSplittingProgressView.as_view(),
        name="scan_image_progress",
    ),
    path(
        "split/<timestamp>/update/",
        BundleSplittingUpdateView.as_view(),
        name="scan_image_update",
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
    path(
        "read/<timestamp>/<int:index>/",
        UpdateQRProgressView.as_view(),
        name="scan_qr_progress",
    ),
    path(
        "read/<timestamp>/alert/",
        QRParsingProgressAlert.as_view(),
        name="scan_qr_alert",
    ),
    path(
        "read/table/<timestamp>/<int:index>/",
        BundleTableView.as_view(),
        name="scan_bundle_table",
    ),
    path(
        "push/<timestamp>/<int:index>/",
        PushPageImage.as_view(),
        name="scan_push_img",
    ),
    path("push/<timestamp>/all/", PushAllPageImages.as_view(), name="scan_push_all"),
    path(
        "push_update/<timestamp>/<int:index>/",
        PagePushingUpdateView.as_view(),
        name="scan_push_update",
    ),
    path(
        "flag/<timestamp>/<int:index>/",
        FlagPageImage.as_view(),
        name="scan_flag_img",
    ),
    path(
        "summary/",
        ScannerSummaryView.as_view(),
        name="scan_summary",
    ),
    path(
        "change/error_state/<timestamp>/<int:index>/",
        ChangeErrorImageState.as_view(),
        name="change_error_state",
    ),
    path(
        "replace/<timestamp>/<int:index>",
        ReplacePageImage.as_view(),
        name="replace_page_image"
    ),
]
