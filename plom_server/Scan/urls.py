# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.urls import path

from .views import (
    ScannerOverview,
    ScannerStagedView,
    ScannerPushedView,
    ScannerCompletePaperView,
    ScannerIncompletePaperView,
    ###
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
    path("overview", ScannerOverview.as_view(), name="scan_overview"),
    path("staged", ScannerStagedView.as_view(), name="scan_list_staged"),
    path("pushed", ScannerPushedView.as_view(), name="scan_list_pushed"),
    path("complete", ScannerCompletePaperView.as_view(), name="scan_list_complete"),
    path(
        "incomplete", ScannerIncompletePaperView.as_view(), name="scan_list_incomplete"
    ),
    ##
    path("", ScannerHomeView.as_view(), name="scan_home"),
    path(
        "bundlepage/<str:the_filter>/<int:bundle_id>/<int:index>/",
        GetBundlePageFragmentView.as_view(),
        name="scan_bundle_page",
    ),
    path(
        "thumbnails/<int:bundle_id>/<int:index>",
        GetBundleThumbnailView.as_view(),
        name="scan_get_thumbnail",
    ),
    path(
        "thumbnails/<str:the_filter>/<int:bundle_id>",
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
    path(
        "discard/<str:the_filter>/<int:bundle_id>/<int:index>/",
        DiscardImageView.as_view(),
        name="discard_image",
    ),
    path(
        "discard_unknowns/<str:the_filter>/<int:bundle_id>/<int:pop_index>/",
        DiscardAllUnknownsHTMXView.as_view(),
        name="discard_all_unknowns",
    ),
    path(
        "unknowify/<str:the_filter>/<int:bundle_id>/<int:index>/",
        UnknowifyImageView.as_view(),
        name="unknowify_image",
    ),
    path(
        "unknowify_discards/<str:the_filter>/<int:bundle_id>/<int:pop_index>/",
        UnknowifyAllDiscardsHTMXView.as_view(),
        name="unknowify_all_discards",
    ),
    path(
        "knowify/<str:the_filter>/<int:bundle_id>/<int:index>/",
        KnowifyImageView.as_view(),
        name="knowify_image",
    ),
    path(
        "extralise/<str:the_filter>/<int:bundle_id>/<int:index>/",
        ExtraliseImageView.as_view(),
        name="extralise_image",
    ),
    path(
        "rotate/clockwise/<str:the_filter>/<int:bundle_id>/<int:index>/",
        RotateImageClockwise.as_view(),
        name="rotate_img_cw",
    ),
    path(
        "rotate/counterclockwise/<str:the_filter>/<int:bundle_id>/<int:index>/",
        RotateImageCounterClockwise.as_view(),
        name="rotate_img_ccw",
    ),
    path(
        "rotate/oneeighty/<str:the_filter>/<int:bundle_id>/<int:index>/",
        RotateImageOneEighty.as_view(),
        name="rotate_img_one_eighty",
    ),
    path(
        "bundle_lock/<int:bundle_id>/",
        BundleLockView.as_view(),
        name="scan_bundle_lock",
    ),
    # Code below IS NOT DEAD - is used in summary_of-pushed.
    path(
        "summary/pushed_img_wrap/<int:img_pk>",
        ScannerPushedImageWrapView.as_view(),
        name="scan_pushed_img_wrap",
    ),
]
