# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

import json
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

from PIL import Image

import plom.scan
from plom.scan import QRextract_legacy, QRextract


def relative_error(x, y) -> float:
    return abs(x - y) / abs(x)


def test_qr_reads_from_image() -> None:
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    q = QRextract(im)
    assert not q["NE"]  # staple
    assert q["NW"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["NW"]["x"], 126) < 0.01
    assert relative_error(q["NW"]["y"], 139) < 0.01
    assert q["SE"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["SE"]["x"], 1419) < 0.001
    assert relative_error(q["SE"]["y"], 1861) < 0.001
    assert q["SW"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["SW"]["x"], 126) < 0.01
    assert relative_error(q["SW"]["y"], 1861) < 0.001


def test_qr_reads_from_image_legacy() -> None:
    im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    p = QRextract_legacy(im, write_to_file=False)
    assert p is not None
    assert not p["NE"]  # staple
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_slight_rotate() -> None:
    # mypy unhappy about `im` changing types here
    _im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = _im.rotate(10, expand=True)
    q = QRextract(im)
    assert not q["NE"]
    assert q["NW"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["NW"]["x"], 148) < 0.01
    assert relative_error(q["NW"]["y"], 384) < 0.01
    assert q["SE"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["SE"]["x"], 1720) < 0.001
    assert relative_error(q["SE"]["y"], 1856) < 0.001
    assert q["SW"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["SW"]["x"], 447) < 0.01
    assert relative_error(q["SW"]["y"], 2080) < 0.001


def test_qr_reads_slight_rotate_legacy() -> None:
    _im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = _im.rotate(10, expand=True)
    p = QRextract_legacy(im, write_to_file=False)
    assert p is not None
    assert not p["NE"]
    assert p["NW"] == ["00002806012823730"]
    assert p["SE"] == ["00002806014823730"]
    assert p["SW"] == ["00002806013823730"]


def test_qr_reads_upside_down() -> None:
    _im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = _im.rotate(180)
    q = QRextract(im)
    assert not q["SW"]
    assert q["SE"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["SE"]["x"], 1420) < 0.001
    assert relative_error(q["SE"]["y"], 1861) < 0.001
    assert q["NW"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["NW"]["x"], 127) < 0.01
    assert relative_error(q["NW"]["y"], 139) < 0.01
    assert q["NE"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["NE"]["x"], 1420) < 0.001
    assert relative_error(q["NE"]["y"], 139) < 0.01


def test_qr_reads_upside_down_legacy() -> None:
    _im = Image.open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = _im.rotate(180)
    p = QRextract_legacy(im, write_to_file=False)
    assert p is not None
    assert not p["SW"]
    assert p["SE"] == ["00002806012823730"]
    assert p["NW"] == ["00002806014823730"]
    assert p["NE"] == ["00002806013823730"]


def test_qr_reads_from_file(tmp_path) -> None:
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    q = QRextract(f)
    assert not q["NE"]
    assert q["NW"]
    assert q["SE"]
    assert q["SW"]


def test_qr_reads_from_file_legacy(tmp_path) -> None:
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    p = QRextract_legacy(f, write_to_file=False)
    assert p is not None
    assert not p["NE"]
    assert p["NW"]
    assert p["SE"]
    assert p["SW"]


def test_qr_reads_write_dot_qr(tmp_path):
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
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
