# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.urls import path

from .views import (
    ScannerHomeView,
    BundleThumbnailsView,
    GetBundleView,
    GetBundlePageFragmentView,
    GetBundleImageView,
    GetBundleThumbnailView,
    GetStagedBundleFragmentView,
    RemoveBundleView,
    ReadQRcodesView,
    PushAllPageImages,
    ScannerSummaryView,
    ScannerPushedImageView,
    ScannerPushedImageWrapView,
    DiscardImageView,
    ExtraliseImageView,
    KnowifyImageView,
    UnknowifyImageView,
    RotateImageClockwise,
    RotateImageCounterClockwise,
    RotateImageOneEighty,
    GetRotatedBundleImageView,
    GetRotatedPushedImageView,
    BundleLockView,
)


urlpatterns = [
    path("", ScannerHomeView.as_view(), name="scan_home"),
    path(
        "bundlepage/<timestamp>/<int:index>/",
        GetBundlePageFragmentView.as_view(),
        name="scan_bundle_page",
    ),
    path(
        "thumbnails/<timestamp>/<int:index>",
        GetBundleThumbnailView.as_view(),
        name="scan_get_thumbnail",
    ),
    path(
        "thumbnails/<int:bundle_id>",
        BundleThumbnailsView.as_view(),
        name="scan_bundle_thumbnails",
    ),
    path(
        "bundle/<timestamp>/",
        GetBundleView.as_view(),
        name="scan_get_bundle",
    ),
    path(
        "bundle_staged/<int:bundle_id>/",
        GetStagedBundleFragmentView.as_view(),
        name="scan_get_staged_bundle_fragment",
    ),
    path(
        "bundle/<timestamp>/<int:index>/",
        GetBundleImageView.as_view(),
        name="scan_get_image",
    ),
    path(
        "bundle_rot/<timestamp>/<int:index>/",
        GetRotatedBundleImageView.as_view(),
        name="scan_get_rotated_image",
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
    path("push/<timestamp>/all/", PushAllPageImages.as_view(), name="scan_push_all"),
    path(
        "summary/",
        ScannerSummaryView.as_view(),
        name="scan_summary",
    ),
    path(
        "summary/pushed_img/<int:img_pk>",
        ScannerPushedImageView.as_view(),
        name="scan_pushed_img",
    ),
    path(
        "summary/rotated_pushed_img/<int:img_pk>",
        GetRotatedPushedImageView.as_view(),
        name="scan_rotated_pushed_img",
    ),
    path(
        "summary/pushed_img_wrap/<int:img_pk>",
        ScannerPushedImageWrapView.as_view(),
        name="scan_pushed_img_wrap",
    ),
    path(
        "discard/<timestamp>/<int:index>/",
        DiscardImageView.as_view(),
        name="discard_image",
    ),
    path(
        "unknowify/<timestamp>/<int:index>/",
        UnknowifyImageView.as_view(),
        name="unknowify_image",
    ),
    path(
        "knowify/<timestamp>/<int:index>/",
        KnowifyImageView.as_view(),
        name="knowify_image",
    ),
    path(
        "extralise/<timestamp>/<int:index>/",
        ExtraliseImageView.as_view(),
        name="extralise_image",
    ),
    path(
        "rotate/clockwise/<timestamp>/<int:index>/",
        RotateImageClockwise.as_view(),
        name="rotate_img_cw",
    ),
    path(
        "rotate/counterclockwise/<timestamp>/<int:index>/",
        RotateImageCounterClockwise.as_view(),
        name="rotate_img_ccw",
    ),
    path(
        "rotate/oneeighty/<timestamp>/<int:index>/",
        RotateImageOneEighty.as_view(),
        name="rotate_img_one_eighty",
    ),
    path(
        "bundle_lock/<timestamp>/",
        BundleLockView.as_view(),
        name="scan_bundle_lock",
    ),
]
