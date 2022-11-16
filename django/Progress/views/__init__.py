# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from .scan_base import BaseScanProgressPage

from .scan_overview import (
    ScanOverview,
    ScanTestPaperProgress,
    ScanGetPageImage,
    ScanTestPageModal,
)

from .scan_colliding import (
    ScanColliding,
    CollidingPagesModal,
    CollisionPageImage,
    DiscardCollidingPage,
    ReplaceImageWithColliding,
)

from .scan_discarded import (
    ScanDiscarded,
    DiscardedPageImage,
    DiscardedPageModal,
    DeleteDiscardedPage,
    RestoreDiscardedPage,
)

from .scan_progress import (
    ScanBundles,
    ScanUnknown,
    ScanError,
    ScanExtra,
)
