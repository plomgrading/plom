# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

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
    WholePaperView,
    PushedImageRotatedView,
    PushedImageWrapView,
    ###
    SubstituteImageView,
    SubstituteImageWrapView,
    ###
    BundleThumbnailsSummaryFragmentView,
    BundleThumbnailsViewNg,
    ThumbnailContainerFragmentView,
    GetBundleView,
    GetBundlePageFragmentViewNg,
    GetBundleThumbnailView,
    GetStagedBundleFragmentView,
    PushAllPageImages,
    DiscardImageViewNg,
    DiscardAllUnknownsHTMXViewNg,
    ExtraliseImageViewNg,
    KnowifyImageViewNg,
    UnknowifyImageViewNg,
    UnknowifyAllDiscardsHTMXViewNg,
    RotateImageView,
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
        "whole_paper/<int:paper_number>",
        WholePaperView.as_view(),
        name="scan_whole_paper",
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
        "bundlepage/<int:bundle_id>/<int:index>/",
        GetBundlePageFragmentViewNg.as_view(),
        name="scan_bundle_page_ng",
    ),
    # TODO: is this different to RotateImageView?
    path(
        "thumbnails/<int:bundle_id>/<int:index>",
        GetBundleThumbnailView.as_view(),
        name="scan_get_thumbnail",
    ),
    path(
        "thumbnail_container/<int:bundle_id>/<int:index>",
        ThumbnailContainerFragmentView.as_view(),
        name="single_thumbnail_container",
    ),
    path(
        "thumbnails/summary-fragment/<int:bundle_id>",
        BundleThumbnailsSummaryFragmentView.as_view(),
        name="scan_bundle_summary",
    ),
    path(
        "thumbnails/<int:bundle_id>",
        BundleThumbnailsViewNg.as_view(),
        name="scan_bundle_thumbnails_ng",
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
        RotateImageView.as_view(),
        name="scan_get_rotated_image",
    ),
    path(
        "push/<int:bundle_id>/all/", PushAllPageImages.as_view(), name="scan_push_all"
    ),
    path(
        "discard_ng/<int:bundle_id>/<int:index>/",
        DiscardImageViewNg.as_view(),
        name="discard_image_ng",
    ),
    path(
        "discard_unknowns/<int:bundle_id>/",
        DiscardAllUnknownsHTMXViewNg.as_view(),
        name="discard_all_unknowns_ng",
    ),
    path(
        "unknowify/<int:bundle_id>/<int:index>/",
        UnknowifyImageViewNg.as_view(),
        name="unknowify_image_ng",
    ),
    path(
        "unknowify_discards/<int:bundle_id>/",
        UnknowifyAllDiscardsHTMXViewNg.as_view(),
        name="unknowify_all_discards_ng",
    ),
    path(
        "knowify/<int:bundle_id>/<int:index>/",
        KnowifyImageViewNg.as_view(),
        name="knowify_image_ng",
    ),
    path(
        "extralise/<int:bundle_id>/<int:index>/",
        ExtraliseImageViewNg.as_view(),
        name="extralise_image_ng",
    ),
    path(
        "rotate/<int:bundle_id>/<int:index>/<int:rotation>",
        RotateImageView.as_view(),
        name="rotate_img",
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
