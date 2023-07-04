# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from django.urls import path

from Progress.views import (
    ScanOverview,
    ScanTestPaperProgress,
    ScanGetPageImage,
    ScanTestPageModal,
    ScanBundles,
    ScanUnknown,
    ScanError,
    ErrorPagesModal,
    ErrorPageImage,
    ScanExtra,
    ScanDiscarded,
    DiscardedPageImage,
    DiscardedPageModal,
    DeleteDiscardedPage,
    RestoreDiscardedPage,
    ProgressIdentifyHome,
    ProgressMarkHome,
    ProgressUserInfoHome,
    IDImageView,
    ClearID,
)


urlpatterns = [
    path("scan/overview/", ScanOverview.as_view(), name="progress_scan_overview"),
    path(
        "scan/overview/<filter_by>",
        ScanTestPaperProgress.as_view(),
        name="progress_scan_tptable",
    ),
    path(
        "scan/overview/<int:test_paper>/<int:index>/img/",
        ScanGetPageImage.as_view(),
        name="progress_scan_page_image",
    ),
    path(
        "scan/overview/<int:test_paper>/<int:index>/",
        ScanTestPageModal.as_view(),
        name="progress_scan_page_modal",
    ),
    path("scan/bundles/", ScanBundles.as_view(), name="progress_scan_bundles"),
    path("scan/unknown/", ScanUnknown.as_view(), name="progress_scan_unknown"),
    path("scan/error/", ScanError.as_view(), name="progress_scan_error"),
    path(
        "scan/error/<int:test_paper>/<int:page_number>/<hash>/",
        ErrorPagesModal.as_view(),
        name="progress_error_modal",
    ),
    path(
        "scan/error/get/<hash>",
        ErrorPageImage.as_view(),
        name="progress_error_image",
    ),
    path("scan/extra/", ScanExtra.as_view(), name="progress_scan_extra"),
    path("scan/discarded/", ScanDiscarded.as_view(), name="progress_scan_discarded"),
    path(
        "scan/discarded/get/<discarded_hash>/",
        DiscardedPageImage.as_view(),
        name="progress_scan_discarded_image",
    ),
    path(
        "scan/discarded/view/<discarded_hash>/",
        DiscardedPageModal.as_view(),
        name="progress_discarded_modal",
    ),
    path(
        "scan/discarded/delete/<discarded_hash>/",
        DeleteDiscardedPage.as_view(),
        name="progress_delete_discarded",
    ),
    path(
        "scan/discarded/restore/<discarded_hash>/",
        RestoreDiscardedPage.as_view(),
        name="progress_restore_discarded",
    ),
    path(
        "mark/overview/",
        ProgressMarkHome.as_view(),
        name="progress_mark_home",
    ),
    path(
        "identify/overview/",
        ProgressIdentifyHome.as_view(),
        name="progress_identify_home",
    ),
    path(
        "identify/overview/id_img/<int:image_pk>",
        IDImageView.as_view(),
        name="ID_img",
    ),
    path(
        "identify/overview/id_img/clear/<int:paper_pk>",
        ClearID.as_view(),
        name="clear_ID",
    ),
    path(
        "userinfo/overview/",
        ProgressUserInfoHome.as_view(),
        name="progress_user_info_home",
    ),
]
