# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from importlib import resources

from plom.common.tpv_utils import (
    encodeExtraPageCode,
    encodeBundleSeparatorPaperCode,
    encodeScrapPaperCode,
)

import plom.scan
from plom.scan import QRextract_corners

from .test_rotations import _PIL_Image_open


def test_qr_reads_micro_QRs(tmp_path) -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_plom_micro_codes.png")
    q = QRextract_corners(im)
    assert q["NW"]["raw_qr_string"] == encodeExtraPageCode(1)
    assert q["NE"]["raw_qr_string"] == encodeExtraPageCode(2)
    assert q["SW"]["raw_qr_string"] == encodeBundleSeparatorPaperCode(3)
    assert q["SE"]["raw_qr_string"] == encodeScrapPaperCode(4)
    assert q["NW"]["tpv"] == "plomX"
    assert q["NE"]["tpv"] == "plomX"
    assert q["SW"]["tpv"] == "plomB"
    assert q["SE"]["tpv"] == "plomS"
