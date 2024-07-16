# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020, 2022, 2024 Colin B. Macdonald
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

"""Utilities for dealing with TPV codes.

A TPV code is a string of 17 digits of the form

  TTTTTPPPVVVOCCCCC
  01234567890123456

This is as much as can be packed into a QR code without
increasing its size.

The format consists of:
  * 01234 = test number
  * 567 = page number
  * 890 = version
  * 1 = position/orientation code
  * 23456 = magic code

A TPV code can be optionally prefixed with "QR-Code:"

  QR-Code:TTTTTPPPVVVOCCCCC

Orientation code:
  * 0 no position information (reserved, unused)
  * 1 NE
  * 2 NW
  * 3 SW
  * 4 SE
  * 5-9 (currently unused)

TODO: might encapsulate position code, have ``getPosition`` return
e.g., the string `"NE"`

Also handles Plom extra page codes. These are alphanumeric stored in micro-qr codes
and are of the form

  sssssO
  012345

where
  * 01234 = "plomX"
  * 5 = orientation
with the orientation code being similar to that used for the TPV
  * 1,5 NE
  * 2,6 NW
  * 3,7 SW
  * 4,8 SE

Also handles Plom scrap-paper codes. These are alphanumeric stored in micro-qr codes
and are of the form

  sssssO
  012345

where
  * 01234 = "plomS"
  * 5 = orientation
with the orientation code being similar to that used for the TPV
  * 1,5 NE
  * 2,6 NW
  * 3,7 SW
  * 4,8 SE
"""

from __future__ import annotations

import random


def isValidTPV(tpv: str) -> bool:
    """Is this a valid TPV code?

    Note that the pyzbar module gives codes with the prefix 'QR-Code:',
    however the zxing-cpp module does not.
    """
    # string prefix is needed for pyzbar but not zxingcpp
    tpv = tpv.lstrip("QR-Code:")
    if len(tpv) != len("TTTTTPPPVVVOCCCCC"):  # todo = remove in future.
        return False
    return tpv.isnumeric()


def isValidExtraPage(tpv: str) -> bool:
    """Is this a valid Extra page code?

    Note that the pyzbar module gives codes with the prefix 'QR-Code:',
    however the zxing-cpp module does not.
    """
    # string prefix is needed for pyzbar but not zxingcpp
    tpv = tpv.lstrip("QR-Code:")
    if len(tpv) != len("plomX9"):  # todo = remove in future.
        return False
    if (tpv[:5] == "plomX") and tpv[5].isnumeric():
        return True
    return False


def parseTPV(tpv: str) -> tuple[int, int, int, str, str]:
    """Parse a TPV string (typically from a QR-code).

    Args:
        tpv: a TPV string of the form "TTTTTPPPVVVOCCCCC",
            typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
        tn (int): test number, up to 5 digits
        pn (int): page group number, up to 3 digits
        vn (int): version number, up to 3 digits
        cn (str): the "magic code", 5 digits zero padded
        o (str): the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    tpv = tpv.lstrip("QR-Code:")  # todo = remove in future.
    tn = int(tpv[0:5])
    pn = int(tpv[5:8])
    vn = int(tpv[8:11])
    o = tpv[11]
    cn = tpv[12:]
    return tn, pn, vn, cn, o


def parseExtraPageCode(expc: str) -> str:
    """Parse an extra page code string (typically from a QR-code).

    Args:
        expc: an extra page code string of the form "plomXO",
            typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
        o: the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    expc = expc.lstrip("QR-Code:")  # todo = remove in future.
    o = int(expc[5])
    if o > 4:
        return str(o - 4)  # todo - keep the 5-8 possibilities
    else:
        return str(o)


def parseScrapPaperCode(scpc: str) -> str:
    """Parse an scrap-paper code string (typically from a QR-code).

    Args:
        scpc: a scrap-paper code string of the form "plomSO",
            typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
        o: the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    scpc = scpc.lstrip("QR-Code:")  # todo = remove in future.
    o = int(scpc[5])
    if o > 4:
        return str(o - 4)  # todo - keep the 5-8 possibilities
    else:
        return str(o)


def getPaperPageVersion(tpv: str) -> str:
    """Return the paper, page, version substring of a TPV string.

    Args:
        tpv: a TPV string of the form "TTTTTPPPVVVOCCCCC",
            typically from a QR-code

    Returns:
        A substring of the original TPV string,
        containing the paper number, page number and version number.
    """
    return tpv[0:11]


def parse_paper_page_version(ppv: str) -> tuple[int, int, int]:
    """Parse string "TTTTTPPPVVV" into paper-number, page-number, version triple.

    Args:
        ppv: a string of the form "TTTTTPPPVVV".

    Returns:
        A triple of integers,
        tn: test number, up to 5 digits,
        pn: page group number, up to 3 digits, and
        vn: version number, up to 3 digits.
    """
    assert len(ppv) == len("TTTTTPPPVVV")
    return (
        int(ppv[:5]),
        int(ppv[5:8]),
        int(ppv[8:11]),
    )


def getPosition(tpv: str) -> int:
    """Return the orientation/position code, which corner the QR code should be located."""
    return int(parseTPV(tpv)[4])


def getCode(tpv: str) -> str:
    """Return the magic code from a TPV string."""
    return parseTPV(tpv)[3]


def encodePaperPageVersion(paper_number: str | int, p: str | int, v: str | int) -> str:
    """Encode three values as the short paper-page-version code.

    Typically used for collision detection.

    Args:
        paper_number: the test number, 0 ≤ test ≤ 99999
        p: page number, 1 ≤ p ≤ 990
        v: version number, 1 ≤ v ≤ 909

    Returns:
        A string of the short page-paper-version code
    """
    assert int(paper_number) >= 0
    assert int(v) >= 1
    assert int(p) >= 1
    paper_number = str(paper_number).zfill(5)
    p = str(p).zfill(3)
    v = str(v).zfill(3)
    assert paper_number.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert len(paper_number) == 5
    assert len(p) == 3
    assert len(v) == 3
    tpv = f"{paper_number}{p}{v}"
    assert len(tpv) == 11
    return tpv


def encodeTPV(
    test: int | str, p: int | str, v: int | str, o: int | str, code: int | str
) -> str:
    """Encode some values as a TPV code.

    Args:
        test: the test number, 0 ≤ test ≤ 99999
        p: page number, 1 ≤ p ≤ 990
        v: version number, 1 ≤ v ≤ 909
        o: position code, 0 ≤ code ≤ 4
        code: magic code, 0 ≤ code ≤ 99999

    Returns:
        A string of the full TPV code.
    """
    assert int(test) >= 0
    assert int(v) >= 1
    assert int(p) >= 1
    assert int(o) >= 0 and int(o) <= 4
    test = str(test).zfill(5)
    p = str(p).zfill(3)
    v = str(v).zfill(3)
    o = str(o)
    code = str(code).zfill(5)
    assert test.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert o.isnumeric()
    assert code.isnumeric()
    assert len(test) == 5
    assert len(p) == 3
    assert len(v) == 3
    assert len(o) == 1
    assert len(code) == 5
    tpv = f"{test}{p}{v}{o}{code}"
    assert len(tpv) == 17
    return tpv


def new_magic_code(seed=None) -> str:
    """Generate a new random magic code.

    Args:
        seed: seed for the random number generator, or ``None`` for
            something reasonable (i.e., current time).

    Returns:
        The magic code, a 5-digit string of digits.
    """
    random.seed(seed)
    magic = str(random.randrange(0, 10**5)).zfill(5)
    assert len(magic) == 5
    return magic


def isValidExtraPageCode(code: str) -> bool:
    """Is this a valid Plom-extra-page code?

    Args:
        code: a string to check.

    Returns:
        The validity of the extra page code.
    """
    code = code.lstrip("plomX")
    if len(code) != len("O"):
        return False
    # now check that remaining letter is a digit in 1,2,..,8.
    if code.isnumeric():
        if 1 <= int(code) <= 8:
            return True
    return False


def isValidScrapPaperCode(code: str) -> bool:
    """Is this a valid Plom-scrap-paper code?

    Args:
        code: a string to check.

    Returns:
        The validity of the scrap page code.
    """
    code = code.lstrip("plomS")
    if len(code) != len("O"):
        return False
    # now check that remaining letter is a digit in 1,2,..,8.
    if code.isnumeric():
        if 1 <= int(code) <= 8:
            return True
    return False


def encodeExtraPageCode(orientation: str | int) -> str:
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom extra page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomX{orientation}"


def encodeScrapPaperCode(orientation: str | int) -> str:
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom extra page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomS{orientation}"


def getExtraPageOrientation(code: str) -> int:
    """Extra the orientation digit from a valid Plom extra page code.

    Args:
        code: a Plom extra page code.

    Returns:
        The orientation as a small integer.
    """
    return int(code[5])


def getScrapPaperOrientation(code: str) -> int:
    """Extra the orientation digit from a valid Plom scrap-paper code.

    Args:
        code: a Plom scrap-paper code.

    Returns:
        The orientation as a small integer.
    """
    return int(code[5])
