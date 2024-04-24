# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer


from __future__ import annotations
from typing import Dict

from Papers.models import ReferenceImage


def get_reference_rectangle(version: int, page: int) -> Dict:
    rimg_obj = ReferenceImage.objects.get(version=version, page_number=page)
    corner_dat = {}
    for cnr in ["NE", "SE", "NW", "SW"]:
        val = rimg_obj.parsed_qr.get(cnr, None)
        if val:
            corner_dat[cnr] = [val["x_coord"], val["y_coord"]]

    return corner_dat
