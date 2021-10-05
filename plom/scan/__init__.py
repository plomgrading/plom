# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

"""
Plom tools associated with scanning papers
"""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom import __version__

from .fasterQRExtract import QRextract

from .checkScanStatus import get_number_of_questions
from .checkScanStatus import check_and_print_scan_status
from .hwSubmissionsCheck import print_who_submitted_what
from .clearScannerLogin import clear_login
from .listBundles import print_bundle_list
from .frontend_scan import processScans, uploadImages
from .frontend_hwscan import processHWScans, processLooseScans, processMissing
from .frontend_hwscan import processAllHWByQ

# what you get from "from plom.scan import *"
__all__ = ["processScans", "uploadImages", "processHWScans", "processMissing"]
