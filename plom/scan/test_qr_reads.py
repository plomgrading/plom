# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pathlib import Path
import pkg_resources
from shutil import copyfile
import json

from PIL import Image

from plom.scan import QRextract


def test_qr_reads_from_image():
    im = Image.open(pkg_resources.resource_stream("plom.scan", "test_zbar_fails.png"))
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]  # staple
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_slight_rotate():
    im = Image.open(pkg_resources.resource_stream("plom.scan", "test_zbar_fails.png"))
    im = im.rotate(10, expand=True)
    p = QRextract(im, write_to_file=False)
    assert not p["NE"]
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_upside_down():
    im = Image.open(pkg_resources.resource_stream("plom.scan", "test_zbar_fails.png"))
    im = im.rotate(180)
    p = QRextract(im, write_to_file=False)
    assert not p["SW"]
    assert p["SE"] == ["00002806012823730"]
    assert p["NW"] == ["00002806014823730"]
    assert p["NE"] == ["00002806013823730"]


def test_qr_reads_from_file():
    f = pkg_resources.resource_filename("plom.scan", "test_zbar_fails.png")
    p = QRextract(f, write_to_file=False)
    assert not p["NE"]  # staple
    assert p["NW"]
    assert p["SE"]
    assert p["SW"]


def test_qr_reads_write_dot_qr(tmpdir):
    oldf = Path(pkg_resources.resource_filename("plom.scan", "test_zbar_fails.png"))
    tmp_path = Path(tmpdir)
    f = tmp_path / oldf.name
    copyfile(oldf, f)
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
    im = Image.open(pkg_resources.resource_stream("plom.scan", "test_zbar_fails.png"))
    p = QRextract(im, write_to_file=False, try_harder=False)
    assert len([x for x in p.values() if x != []]) == 2  # only 2 not 3
