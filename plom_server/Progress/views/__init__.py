# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from .scan_base import BaseScanProgressPage

from .scan_overview import (
    ScanOverview,
    ScanBundlesView,
)

from .scan_complete import ScanCompleteView, PushedImageView, PushedImageWrapView
from .scan_incomplete import ScanIncompleteView
from .scan_discards import ScanDiscardView, ScanReassignView

from .progress_identify import (
    ProgressIdentifyHome,
    IDImageView,
    ClearID,
    IDImageWrapView,
)

from .progress_mark import (
    ProgressMarkHome,
    ProgressMarkStatsView,
    ProgressMarkDetailsView,
)

from .progress_userinfo import (
    ProgressUserInfoHome,
)
