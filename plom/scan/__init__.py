# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

"""Plom tools associated with scanning papers."""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom import __version__

from .fasterQRExtract import QRextract_legacy, QRextract

from .start_messenger import start_messenger, with_scanner_messenger
from .checkScanStatus import check_and_print_scan_status
from .hwSubmissionsCheck import print_who_submitted_what
from .clearScannerLogin import clear_login
from .listBundles import get_bundle_list, print_bundle_list
from .frontend_scan import processScans, uploadImages
from .frontend_hwscan import processHWScans, processMissing
from .frontend_hwscan import processAllHWByQ
from .scansToImages import processFileToBitmaps
from .scansToImages import try_to_extract_image, render_page_to_bitmap
from .rotate import rotate_bitmap

# what you get from "from plom.scan import *"
__all__ = [
    "processScans",
    "uploadImages",
    "processHWScans",
    "processMissing",
    "processFileToBitmaps",
    "try_to_extract_image",
    "render_page_to_bitmap",
    "get_bundle_list",
    "print_bundle_list",
    "QRextract_legacy",
    "QRextract",
    "rotate_bitmap",
]
