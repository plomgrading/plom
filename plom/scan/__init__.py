# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023, 2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

"""Plom tools associated with scanning papers."""

__copyright__ = "Copyright (C) 2018-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom.common import __version__

# Image types we expect the client to be able to handle, in lowercase
# TODO: think about JBIG, etc: other stuff that commonly lives in PDF
PlomImageExts = ("png", "jpg", "jpeg")

# This used to be shared with Client; don't think they need to match
DefaultPixelHeight = 2000

from .fasterQRExtract import QRextract_legacy, QRextract
from .scansToImages import processFileToBitmaps
from .scansToImages import try_to_extract_image, render_page_to_bitmap
from .rotate import rotate_bitmap

# what you get from "from plom.scan import *"
__all__ = [
    "processFileToBitmaps",
    "QRextract",
    "rotate_bitmap",
]
