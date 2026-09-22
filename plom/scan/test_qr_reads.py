# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2026 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2026 Jax Lim

from importlib import resources

import plom.scan
from plom.scan import QRextract_corners, QRextract_list

from .test_rotations import _PIL_Image_open


def relative_error(x, y) -> float:
    return abs(x - y) / abs(x)


def test_qr_reads_from_image() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_zbar_fails.png")
    q = QRextract_corners(im)
    rot = 0
    assert not q.get("NE")  # staple
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
    q = QRextract_corners(im)
    assert not q.get("NE")
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
    q = QRextract_corners(im)
    assert not q.get("SW")
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
    q = QRextract_corners(im)
    # ZXing-cpp gives nearest integer orientation
    assert q["NW"]["orientation"] == round(rot)


def test_qr_reads_from_file(tmp_path) -> None:
    b = (resources.files(plom.scan) / "test_zbar_fails.png").read_bytes()
    f = tmp_path / "test_zbar.png"
    with open(f, "wb") as fh:
        fh.write(b)
    q = QRextract_corners(f)
    assert not q.get("NE")
    assert q["NW"]
    assert q["SE"]
    assert q["SW"]


def test_qr_reads_from_image_ignore_microqr_near_or_in_good_qr() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_nearby_microqr.png")
    qrs = QRextract_list(im)

    (f,) = [q for q in qrs if q["raw_qr_string"] == "hello"]
    assert f["ignore"]
    assert f["corner_guess_from_position"] == "SW"
    (f,) = [q for q in qrs if q["raw_qr_string"] == "goodbye"]
    assert f["ignore"]
    assert f["corner_guess_from_position"] == "SW"

    (f,) = [q for q in qrs if q["raw_qr_string"] == "abcdef"]
    assert not f["ignore"]
    assert f["corner_guess_from_position"] == "??"

    (f,) = [q for q in qrs if q["corner_guess_from_position"] == "NE"]
    assert not f["ignore"]
    assert f["format"] == "Micro QR Code"
    assert f["content_type"] == "Binary"

    # depends on https://github.com/zxing-cpp/zxing-cpp/issues/1162
    # with Zxing 3.0.0, 3.1.1 there is a halucinated microQR in the SE
    ignores = [q for q in qrs if q["ignore"]]
    assert len(ignores) in (2, 3)

    for q in ignores:
        assert q["corner_guess_from_position"] in ("SE", "SW")


def test_qr_reads_from_image_ignore_microqr_near_or_in_good_qr_corners() -> None:
    im = _PIL_Image_open(resources.files(plom.scan) / "test_nearby_microqr.png")
    q = QRextract_corners(im)
    assert not q.get("NW")

    assert q["NE"]["format"] == "Micro QR Code"
    assert q["NE"]["page_type"] == "invalid_qr"
    assert not q["NE"]["ignore"]

    assert q["SE"]["format"] == "QR Code"
    assert q["SE"]["page_type"] == "plom_qr"
    assert not q["SE"]["ignore"]

    assert q["SW"]["format"] == "QR Code"
    assert q["SW"]["page_type"] == "plom_qr"
    assert not q["SW"]["ignore"]

    assert "other1" in q.keys()
    assert "other2" in q.keys()
    assert "other3" in q.keys()
    # there might be other4 as well, see zxing-cpp/issues/1162 above

    for k, v in q.items():
        if "other" in k:
            assert v["format"] == "Micro QR Code"
