# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2026 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2026 Jax Lim

from importlib import resources

import plom.scan
from plom.scan import QRextract

from .test_rotations import _PIL_Image_open


def relative_error(x, y) -> float:
    return abs(x - y) / abs(x)


def test_qr_reads_from_image() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    q = QRextract(im)
    rot = 0
    assert not q["NE"]  # staple
    assert q["NW"]["raw_qr_string"] == "00002806012823730"
    assert relative_error(q["NW"]["x_coord"], 126) < 0.01
    assert relative_error(q["NW"]["y_coord"], 139) < 0.01
    assert abs(q["NW"]["orientation"] - rot) < 0.05
    assert q["SE"]["raw_qr_string"] == "00002806014823730"
    assert relative_error(q["SE"]["x_coord"], 1419) < 0.001
    assert relative_error(q["SE"]["y_coord"], 1861) < 0.001
    assert abs(q["SE"]["orientation"] - rot) < 0.05

    assert q["SW"]["raw_qr_string"] == "00002806013823730"
    assert relative_error(q["SW"]["x_coord"], 126) < 0.01
    assert relative_error(q["SW"]["y_coord"], 1861) < 0.001
    assert abs(q["SW"]["orientation"] - rot) < 0.05


def test_qr_reads_slight_rotate() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    rot = 10  # 10 degrees ccw
    im = im.rotate(rot, expand=True)
    q = QRextract(im)
    assert not q["NE"]
    assert q["NW"]["raw_qr_string"] == "00002806012823730"
    assert relative_error(q["NW"]["x_coord"], 148) < 0.01
    assert relative_error(q["NW"]["y_coord"], 384) < 0.01
    assert abs(q["NW"]["orientation"] - rot) < 0.05
    assert q["SE"]["raw_qr_string"] == "00002806014823730"
    assert relative_error(q["SE"]["x_coord"], 1720) < 0.001
    assert relative_error(q["SE"]["y_coord"], 1856) < 0.001
    assert abs(q["SE"]["orientation"] - rot) < 0.05
    assert q["SW"]["raw_qr_string"] == "00002806013823730"
    assert relative_error(q["SW"]["x_coord"], 447) < 0.01
    assert relative_error(q["SW"]["y_coord"], 2080) < 0.001
    assert abs(q["SW"]["orientation"] - rot) < 0.05


def test_qr_reads_upside_down() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    rot = 180
    im = im.rotate(rot)
    q = QRextract(im)
    assert not q["SW"]
    assert q["SE"]["raw_qr_string"] == "00002806012823730"
    assert relative_error(q["SE"]["x_coord"], 1420) < 0.001
    assert relative_error(q["SE"]["y_coord"], 1861) < 0.001
    assert abs(q["SE"]["orientation"] - rot) % 360 < 0.05
    assert q["NW"]["raw_qr_string"] == "00002806014823730"
    assert relative_error(q["NW"]["x_coord"], 127) < 0.01
    assert relative_error(q["NW"]["y_coord"], 139) < 0.01
    assert abs(q["NW"]["orientation"] - rot) % 360 < 0.05
    assert q["NE"]["raw_qr_string"] == "00002806013823730"
    assert relative_error(q["NE"]["x_coord"], 1420) < 0.001
    assert relative_error(q["NE"]["y_coord"], 139) < 0.01
    assert abs(q["NE"]["orientation"] - rot) % 360 < 0.05


def test_qr_reads_float_rotate() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    rot = 6.25
    im = im.rotate(rot, expand=True)
    q = QRextract(im)
    # ZXing-cpp gives nearest integer orientation
    assert q["NW"]["orientation"] == round(rot)


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
