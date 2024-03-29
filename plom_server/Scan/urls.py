# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
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
    ReadQRcodesView,
    PushAllPageImages,
    ScannerSummaryView,
    ScannerPushedImageView,
    ScannerPushedImageWrapView,
    DiscardImageView,
    DiscardAllUnknownsHTMXView,
    ExtraliseImageView,
    KnowifyImageView,
    UnknowifyImageView,
    UnknowifyAllDiscardsHTMXView,
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
        "bundlepage/<int:bundle_id>/<int:index>/",
        GetBundlePageFragmentView.as_view(),
        name="scan_bundle_page",
    ),
    path(
        "thumbnails/<int:bundle_id>/<int:index>",
        GetBundleThumbnailView.as_view(),
        name="scan_get_thumbnail",
    ),
    path(
        "thumbnails/<int:bundle_id>",
        BundleThumbnailsView.as_view(),
        name="scan_bundle_thumbnails",
    ),
    path(
        "bundle/<int:bundle_id>/",
        GetBundleView.as_view(),
        name="scan_get_bundle",
    ),
    path(
        "bundle_staged/<int:bundle_id>/",
        GetStagedBundleFragmentView.as_view(),
        name="scan_get_staged_bundle_fragment",
    ),
    path(
        "bundle/<int:bundle_id>/<int:index>/",
        GetBundleImageView.as_view(),
        name="scan_get_image",
    ),
    path(
        "bundle_rot/<int:bundle_id>/<int:index>/",
        GetRotatedBundleImageView.as_view(),
        name="scan_get_rotated_image",
    ),
    path(
        "read/<int:bundle_id>",
        ReadQRcodesView.as_view(),
        name="scan_read_qr",
    ),
    path(
        "push/<int:bundle_id>/all/", PushAllPageImages.as_view(), name="scan_push_all"
    ),
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
    # TODO: currently dead unused code?
    path(
        "summary/pushed_img_wrap/<int:img_pk>",
        ScannerPushedImageWrapView.as_view(),
        name="scan_pushed_img_wrap",
    ),
    path(
        "discard/<int:bundle_id>/<int:index>/",
        DiscardImageView.as_view(),
        name="discard_image",
    ),
    path(
        "discard_unknowns/<int:bundle_id>/<int:pop_index>/",
        DiscardAllUnknownsHTMXView.as_view(),
        name="discard_all_unknowns",
    ),
    path(
        "unknowify/<int:bundle_id>/<int:index>/",
        UnknowifyImageView.as_view(),
        name="unknowify_image",
    ),
    path(
        "unknowify_discards/<int:bundle_id>/<int:pop_index>/",
        UnknowifyAllDiscardsHTMXView.as_view(),
        name="unknowify_all_discards",
    ),
    path(
        "knowify/<int:bundle_id>/<int:index>/",
        KnowifyImageView.as_view(),
        name="knowify_image",
    ),
    path(
        "extralise/<int:bundle_id>/<int:index>/",
        ExtraliseImageView.as_view(),
        name="extralise_image",
    ),
    path(
        "rotate/clockwise/<int:bundle_id>/<int:index>/",
        RotateImageClockwise.as_view(),
        name="rotate_img_cw",
    ),
    path(
        "rotate/counterclockwise/<int:bundle_id>/<int:index>/",
        RotateImageCounterClockwise.as_view(),
        name="rotate_img_ccw",
    ),
    path(
        "rotate/oneeighty/<int:bundle_id>/<int:index>/",
        RotateImageOneEighty.as_view(),
        name="rotate_img_one_eighty",
    ),
    path(
        "bundle_lock/<int:bundle_id>/",
        BundleLockView.as_view(),
        name="scan_bundle_lock",
    ),
]
