# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy
# Copyright (C) 2025 Deep Shah

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
    BundleThumbnailsView,
    ThumbnailContainerFragmentView,
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
    RotateImageView,
    BundleLockView,
    BundlePushCollisionView,
    BundlePushBadErrorView,
    RecentStagedBundleRedirectView,
    HandwritingComparisonView,
    GeneratePaperPDFView,
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
        GetBundlePageFragmentView.as_view(),
        name="scan_bundle_page",
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
        RotateImageView.as_view(),
        name="scan_get_rotated_image",
    ),
    path(
        "push/<int:bundle_id>/all/", PushAllPageImages.as_view(), name="scan_push_all"
    ),
    path(
        "discard/<int:bundle_id>/<int:index>/",
        DiscardImageView.as_view(),
        name="discard_image",
    ),
    path(
        "discard_unknowns/<int:bundle_id>/",
        DiscardAllUnknownsHTMXView.as_view(),
        name="discard_all_unknowns",
    ),
    path(
        "unknowify/<int:bundle_id>/<int:index>/",
        UnknowifyImageView.as_view(),
        name="unknowify_image",
    ),
    path(
        "unknowify_discards/<int:bundle_id>/",
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
    path(
        "compare-handwriting/<int:bundle_id>/<int:index>/",
        HandwritingComparisonView.as_view(),
        name="scan_compare_handwriting",
    ),
    path(
        "paper-pdf/<int:bundle_id>/<int:paper_number>/",
        GeneratePaperPDFView.as_view(),
        name="scan_paper_pdf",
    ),
]
