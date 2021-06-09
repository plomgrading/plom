# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Colin B. Macdonald

"""
Plom tools associated with scanning papers
"""

__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from .rotate import rotateBitmap
from .fasterQRExtract import QRextract
from .readQRCodes import reOrientPage, decode_QRs_in_image_files

from .sendUnknownsToServer import (
    upload_unknowns,
    print_unknowns_warning,
    bundle_has_nonuploaded_unknowns,
)
from .sendCollisionsToServer import (
    upload_collisions,
    print_collision_warning,
    bundle_has_nonuploaded_collisions,
)
from .sendPagesToServer import bundle_name_from_filename, bundle_name_and_md5
from .checkScanStatus import get_number_of_questions
