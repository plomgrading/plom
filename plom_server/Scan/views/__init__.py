# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Deep Shah
# Copyright (C) 2025 Aidan Murphy

"""Views of the Plom Server Scan app."""

from .scanner_home import (
    ScannerOverview,
    ScannerStagedView,
    ScannerPushedView,
    ScannerUploadView,
    ##
    GetBundleView,
    GetStagedBundleFragmentView,
)
from .scan_discards import ScannerDiscardView, ScannerReassignView

from .pushed_images import (
    PushedImageView,
    WholePaperView,
    PushedImageRotatedView,
    PushedImageWrapView,
    SubstituteImageView,
    SubstituteImageWrapView,
)

from .manage_bundle import (
    GetBundlePageFragmentView,
    ThumbnailContainerFragmentView,
    BundleThumbnailsView,
    BundleThumbnailsSummaryFragmentView,
    GetBundleThumbnailView,
    BundleLockView,
    BundlePushCollisionView,
    BundlePushBadErrorView,
    RecentStagedBundleRedirectView,
    HandwritingComparisonView,
    GeneratePaperPDFView,
)

from .push_images import (
    PushAllPageImages,
)


from .scanner_summary import (
    ScannerCompletePaperView,
    ScannerIncompletePaperView,
)

from .cast_image_state import (
    DiscardImageView,
    DiscardAllUnknownsHTMXView,
    ExtraliseImageView,
    KnowifyImageView,
    UnknowifyImageView,
    UnknowifyAllDiscardsHTMXView,
)

from .rotate_images import RotateImageView
