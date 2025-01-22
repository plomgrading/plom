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
    ScannerUploadView,
    ScannerCompletePaperView,
    ScannerIncompletePaperView,
    ###
    ScannerDiscardView,
    ScannerReassignView,
    ###
    PushedImageView,
    DiscardWholePaperView,
    PushedImageRotatedView,
    PushedImageWrapView,
    ###
    SubstituteImageView,
    SubstituteImageWrapView,
    ###
    BundleThumbnailsView,
    GetBundleView,
    GetBundlePageFragmentView,
    GetBundleThumbnailView,
    GetStagedBundleFragmentView,
    PushAllPageImages,
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
    BundlePushCollisionView,
    BundlePushBadErrorView,
    RecentStagedBundleRedirectView,
)


urlpatterns = [
    path("overview", ScannerOverview.as_view(), name="scan_overview"),
    path("upload", ScannerUploadView.as_view(), name="scan_upload"),
    path("staged", ScannerStagedView.as_view(), name="scan_list_staged"),
    path("pushed", ScannerPushedView.as_view(), name="scan_list_pushed"),
    path("complete", ScannerCompletePaperView.as_view(), name="scan_list_complete"),
    path(
        "incomplete", ScannerIncompletePaperView.as_view(), name="scan_list_incomplete"
    ),
    path(
        "recent_staged_bundle",
        RecentStagedBundleRedirectView.as_view(),
        name="scan_recent_bundle_thumbnails",
    ),
    ##
    path(
        "discard/",
        ScannerDiscardView.as_view(),
        name="scan_list_discard",
    ),
    path(
        "reassign/<int:page_pk>",
        ScannerReassignView.as_view(),
        name="reassign_discard",
    ),
    ##
    path(
        "pushed_img/<int:img_pk>",
        PushedImageView.as_view(),
        name="pushed_img",
    ),
    path(
        "discard_whole/<int:paper_number>",
        DiscardWholePaperView.as_view(),
        name="scan_discard_whole_paper",
    ),
    path(
        "pushed_img_rot/<int:img_pk>",
        PushedImageRotatedView.as_view(),
        name="pushed_img_rot",
    ),
    path(
        "pushed_img_wrap/<str:page_kind>/<int:page_pk>",
        PushedImageWrapView.as_view(),
        name="pushed_img_wrap",
    ),
    path(
        "substitute_img/<int:img_pk>",
        SubstituteImageView.as_view(),
        name="substitute_img",
    ),
    path(
        "substitute_img_wrap/<int:paper>/<int:page>",
        SubstituteImageWrapView.as_view(),
        name="substitute_img_wrap",
    ),
    ##
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
        # note post triggers qr-read, and delete triggers bundle delete.
    ),
    path(
        "bundle_rot/<int:bundle_id>/<int:index>/",
        GetRotatedBundleImageView.as_view(),
        name="scan_get_rotated_image",
    ),
    path(
        "push/<int:bundle_id>/all/", PushAllPageImages.as_view(), name="scan_push_all"
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
    path(
        "bundle_push_collision/<int:bundle_id>/",
        BundlePushCollisionView.as_view(),
        name="scan_bundle_push_collision",
    ),
    path(
        "bundle_push_error/<int:bundle_id>/",
        BundlePushBadErrorView.as_view(),
        name="scan_bundle_push_error",
    ),
]
