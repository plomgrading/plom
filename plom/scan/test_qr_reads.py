# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pathlib import Path
import json
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PIL import Image

import plom.scan
from plom.scan import QRextract


def test_qr_reads_from_image():
    with resources.open_binary(plom.scan, "test_zbar_fails.png") as f:
        im = Image.open(f)
        im.load()
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]  # staple
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_slight_rotate():
    with resources.open_binary(plom.scan, "test_zbar_fails.png") as f:
        im = Image.open(f)
        im.load()
    im = im.rotate(10, expand=True)
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_upside_down():
    with resources.open_binary(plom.scan, "test_zbar_fails.png") as f:
        im = Image.open(f)
        im.load()
    im = im.rotate(180)
    p = QRextract(im, write_to_file=False)
    assert not p["SW"]
    assert p["SE"] == ["00002806012823730"]
    assert p["NW"] == ["00002806014823730"]
    assert p["NE"] == ["00002806013823730"]


def test_qr_reads_from_file(tmpdir):
    b = resources.read_binary(plom.scan, "test_zbar_fails.png")
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
    b = resources.read_binary(plom.scan, "test_zbar_fails.png")
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


def test_qr_reads_one_fails():
    """This test may be sensitive to ZBar version, machine, etc.

    Test could be removed if issue is fixed in the future.
    """
    with resources.open_binary(plom.scan, "test_zbar_fails.png") as f:
        im = Image.open(f)
        im.load()
    p = QRextract(im, write_to_file=False, try_harder=False)
    assert len([x for x in p.values() if x != []]) == 2  # only 2 not 3
