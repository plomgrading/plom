# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023 Colin B. Macdonald

"""
Plom tools associated with scanning papers
"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom import __version__

from .fasterQRExtract import QRextract

from .start_messenger import start_messenger, with_scanner_messenger
from .checkScanStatus import check_and_print_scan_status
from .hwSubmissionsCheck import print_who_submitted_what
from .clearScannerLogin import clear_login
from .listBundles import get_bundle_list, print_bundle_list
from .frontend_scan import processScans, uploadImages
from .frontend_hwscan import processHWScans, processMissing
from .frontend_hwscan import processAllHWByQ
from .scansToImages import processFileToBitmaps

# what you get from "from plom.scan import *"
__all__ = [
    "processScans",
    "uploadImages",
    "processHWScans",
    "processMissing",
    "processFileToBitmaps",
    "get_bundle_list",
    "print_bundle_list",
]
