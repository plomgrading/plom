# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

import json
from pathlib import Path
import sys

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PIL import Image

import plom.scan
from plom.scan import QRextract


def test_qr_reads_from_image():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]  # staple
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_slight_rotate():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(10, expand=True)
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_upside_down():
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im.load()
    im = im.rotate(180)
    p = QRextract(im, write_to_file=False)
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
    p = QRextract(f, write_to_file=False)
    assert not p["NE"]  # staple
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
    p = QRextract(f, write_to_file=True)
    assert qrfile.exists()
    with open(qrfile, "r") as f:
        J = json.load(f)
    assert p == J  # .png.qr matches return values
