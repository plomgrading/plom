# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.urls import path

from Progress.views import (
    ScanOverview,
    ScanTestPaperProgress,
    ScanGetPageImage,
    ScanTestPageModal,
    ScanBundles,
    ScanColliding,
    CollidingPagesModal,
    CollisionPageImage,
    ScanUnknown,
    ScanError,
    ErrorPagesModal,
    ScanExtra,
    ScanDiscarded,
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
    path("scan/colliding/", ScanColliding.as_view(), name="progress_scan_colliding"),
    path(
        "scan/colliding/<int:test_paper>/<int:index>/<timestamp>/<username>/<int:order>/",
        CollidingPagesModal.as_view(),
        name="progress_colliding_modal",
    ),
    path(
        "scan/colliding/<timestamp>/<username>/<int:order>/",
        CollisionPageImage.as_view(),
        name="progress_collision_image",
    ),
    path("scan/unknown/", ScanUnknown.as_view(), name="progress_scan_unknown"),
    path("scan/error/", ScanError.as_view(), name="progress_scan_error"),
    path(
        "scan/error/<int:test_paper>/<int:page_number>/<hash>/", 
        ErrorPagesModal.as_view(), 
        name="progress_error_modal"
    ),
    path("scan/extra/", ScanExtra.as_view(), name="progress_scan_extra"),
    path("scan/discarded/", ScanDiscarded.as_view(), name="progress_scan_discarded"),
]
