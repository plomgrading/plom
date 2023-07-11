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
    ErrorPagesModal,
    ErrorPageImage,
    ScanDiscarded,
    DiscardedPageImage,
    DiscardedPageModal,
    DeleteDiscardedPage,
    RestoreDiscardedPage,
    ProgressIdentifyHome,
    ProgressMarkHome,
    ProgressUserInfoHome,
    IDImageView,
    IDImageWrapView,
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
        "identify/overview/id_img_wrap/<int:image_pk>",
        IDImageWrapView.as_view(),
        name="ID_img_wrap",
    ),
    path(
        "userinfo/overview/",
        ProgressUserInfoHome.as_view(),
        name="progress_user_info_home",
    ),
]
