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
    assert q["NW"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["NW"]["x"], 126) < 0.01
    assert relative_error(q["NW"]["y"], 139) < 0.01
    assert abs(q["NW"]["orientation"], rot) < 0.05
    assert q["SE"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["SE"]["x"], 1419) < 0.001
    assert relative_error(q["SE"]["y"], 1861) < 0.001
    assert abs(q["SE"]["orientation"], rot) < 0.05

    assert q["SW"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["SW"]["x"], 126) < 0.01
    assert relative_error(q["SW"]["y"], 1861) < 0.001
    assert abs(q["SW"]["orientation"], rot) < 0.05


def test_qr_reads_slight_rotate() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = im.rotate(10, expand=True)
    q = QRextract(im)
    rot = -10
    assert not q["NE"]
    assert q["NW"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["NW"]["x"], 148) < 0.01
    assert relative_error(q["NW"]["y"], 384) < 0.01
    assert abs(q["NW"]["orientation"], rot) < 0.05
    assert q["SE"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["SE"]["x"], 1720) < 0.001
    assert relative_error(q["SE"]["y"], 1856) < 0.001
    assert abs(q["SE"]["orientation"], rot) < 0.05
    assert q["SW"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["SW"]["x"], 447) < 0.01
    assert relative_error(q["SW"]["y"], 2080) < 0.001
    assert abs(q["SW"]["orientation"], rot) < 0.05


def test_qr_reads_upside_down() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = im.rotate(180)
    q = QRextract(im)
    rot = -180
    assert not q["SW"]
    assert q["SE"]["tpv_signature"] == "00002806012823730"
    assert relative_error(q["SE"]["x"], 1420) < 0.001
    assert relative_error(q["SE"]["y"], 1861) < 0.001
    assert abs(q["SE"]["orientation"], rot) < 0.05
    assert q["NW"]["tpv_signature"] == "00002806014823730"
    assert relative_error(q["NW"]["x"], 127) < 0.01
    assert relative_error(q["NW"]["y"], 139) < 0.01
    assert abs(q["NW"]["orientation"], rot) < 0.05
    assert q["NE"]["tpv_signature"] == "00002806013823730"
    assert relative_error(q["NE"]["x"], 1420) < 0.001
    assert relative_error(q["NE"]["y"], 139) < 0.01
    assert abs(q["NE"]["orientation"], rot) < 0.05


def test_qr_reads_float_rotate() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    im = im.rotate(6.25, expand=True)

    q = QRextract(im)
    print(type(q["NW"]["orientation"]))
    print(q)


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
