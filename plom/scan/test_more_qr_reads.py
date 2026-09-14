# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald


from plom.scan.qr_extract import _assign_corners

# Maintenance note: these are really tests of `QRextract` but with
# mock output from `QRextract_list`.  Lots internal details of the
# returns of `QRextract_list` here b/c we're testing an internal
# helper function `_assign_corners`.  These tests can be updated if
# those details change.


def test_qr_corners_assigned() -> None:

    L = [
        {
            "raw_qr_string": "00002806012823730",
            "x_coord": 126.25,
            "y_coord": 139.25,
            "corner_guess_from_position": "NW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "00002806013823730",
            "x_coord": 126.25,
            "y_coord": 1861.25,
            "corner_guess_from_position": "SW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "00002806014823730",
            "x_coord": 1419.25,
            "y_coord": 1861.25,
            "corner_guess_from_position": "SE",
            "page_type": "plom_qr",
        },
    ]
    q = _assign_corners(L)
    assert not q.get("NE")
    assert q["NW"]["raw_qr_string"] == "00002806012823730"
    assert q["SE"]["raw_qr_string"] == "00002806014823730"
    assert q["SW"]["raw_qr_string"] == "00002806013823730"


def test_qr_corners_extras() -> None:
    L = [
        {
            "raw_qr_string": "00002806012823730",
            "corner_guess_from_position": "NW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "00002806013823730",
            "corner_guess_from_position": "SW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "00002806014823730",
            "corner_guess_from_position": "SE",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "hello",
            "corner_guess_from_position": "??",
            "page_type": "invalid_qr",
        },
    ]
    q = _assign_corners(L)
    assert q["other1"]["raw_qr_string"] == "hello"


def test_qr_corners_plom_qr_pages_come_first() -> None:
    L = [
        {
            "raw_qr_string": "00002806012823730",
            "corner_guess_from_position": "NW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "00002806013823730",
            "corner_guess_from_position": "SW",
            "page_type": "plom_qr",
        },
        {
            "raw_qr_string": "hello",
            "corner_guess_from_position": "SE",
            "page_type": "invalid_qr",
        },
        {
            "raw_qr_string": "00002806014823730",
            "corner_guess_from_position": "SE",
            "page_type": "plom_qr",
        },
    ]
    q = _assign_corners(L)
    assert q["SE"]["raw_qr_string"] == "00002806014823730"
    assert q["other1"]["raw_qr_string"] == "hello"
