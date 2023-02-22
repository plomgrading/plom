# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

import json
from pathlib import Path
import sys

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PIL import Image

import plom.scan
from plom.scan import QRextract_legacy, QRextract


def test_qr_reads_from_image():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    q = QRextract(im)
    assert not q["NE"]  # staple
    assert q["NW"] == {"tpv_signature": "00002806012823730", "x": 126, "y": 139}
    assert q["SE"] == {"tpv_signature": "00002806014823730", "x": 1419, "y": 1861}
    assert q["SW"] == {"tpv_signature": "00002806013823730", "x": 126, "y": 1861}


def test_qr_reads_from_image_legacy():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    p = QRextract_legacy(im, write_to_file=False)
    assert not p["NE"]  # staple
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_slight_rotate():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(10, expand=True)
    q = QRextract(im)
    assert not q["NE"]
    assert q["NW"] == {"tpv_signature": "00002806012823730", "x": 148, "y": 384}
    assert q["SE"] == {"tpv_signature": "00002806014823730", "x": 1720, "y": 1856}
    assert q["SW"] == {"tpv_signature": "00002806013823730", "x": 447, "y": 2080}


def test_qr_reads_slight_rotate_legacy():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(10, expand=True)
    p = QRextract_legacy(im, write_to_file=False)
    assert not p["NE"]
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_upside_down():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(180)
    q = QRextract(im)
    assert not q["SW"]
    assert q["SE"] == {"tpv_signature": "00002806012823730", "x": 1420, "y": 1861}
    assert q["NW"] == {"tpv_signature": "00002806014823730", "x": 127, "y": 139}
    assert q["NE"] == {"tpv_signature": "00002806013823730", "x": 1420, "y": 139}


def test_qr_reads_upside_down_legacy():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(180)
    p = QRextract_legacy(im, write_to_file=False)
    assert not p["SW"]
    assert p["SE"] == ["00002806012823730"]
    assert p["NW"] == ["00002806014823730"]
    assert p["NE"] == ["00002806013823730"]


def test_qr_reads_from_file(tmpdir):
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    tmp_path = Path(tmpdir)
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    q = QRextract(f)
    assert not q["NE"]
    assert q["NW"]
    assert q["SE"]
    assert q["SW"]


def test_qr_reads_from_file_legacy(tmpdir):
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    tmp_path = Path(tmpdir)
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    p = QRextract_legacy(f, write_to_file=False)
    assert not p["NE"]
    assert p["NW"]
    assert p["SE"]
    assert p["SW"]


def test_qr_reads_write_dot_qr(tmpdir):
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    tmp_path = Path(tmpdir)
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    qrfile = f.with_suffix(".png.qr")  # has funny extension
    assert not qrfile.exists()
    p = QRextract_legacy(f, write_to_file=True)
    assert qrfile.exists()
    with open(qrfile, "r") as f:
        J = json.load(f)
    assert p == J  # .png.qr matches return values
