# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020, 2022, 2024-2025 Colin B. Macdonald
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

"""Utilities for dealing with TPV codes.

A TPV code is a string of 17 digits of the form

  TTTTTPPPVVOCCCCCC
  01234567890123456

This is as much as can be packed into a QR code without
increasing its size.

The format consists of:
  * 01234 = paper number (formerly "test number")
  * 567 = page number
  * 89 = version
  * 0 = position/orientation code
  * 123456 = magic code

A TPV code can be optionally prefixed with "QR-Code:"

  QR-Code:TTTTTPPPVVOCCCCCC

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

Also handles Plom bundle-separator-paper codes. These are alphanumeric stored in
micro-qr codes and are of the form

  sssssO
  012345

where
  * 01234 = "plomB"
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
    if len(tpv) != len("TTTTTPPPVVOCCCCCC"):  # todo = remove in future.
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
        tpv: a TPV string of the form "TTTTTPPPVVOCCCCCC",
            typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
        tn (int): paper number, up to 5 digits (formerly "test number")
        pn (int): page group number, up to 3 digits
        vn (int): version number, up to 2 digits
        cn (str): the "magic code", 6 digits zero padded
        o (str): the orientation code
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    tpv = tpv.lstrip("QR-Code:")  # todo = remove in future.
    tn = int(tpv[0:5])
    pn = int(tpv[5:8])
    vn = int(tpv[8:10])
    o = tpv[10]
    cn = tpv[11:]
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
    """Parse a scrap-paper code string (typically from a QR-code).

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


def parseBundleSeparatorPaperCode(bspc: str) -> str:
    """Parse a bundle-separator-paper code string (typically from a QR-code).

    Args:
        bspc: a bundle-separator-paper code string of the form "plomBO",
            typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
        o: the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    bspc = bspc.lstrip("QR-Code:")  # todo = remove in future.
    o = int(bspc[5])
    if o > 4:
        return str(o - 4)  # todo - keep the 5-8 possibilities
    else:
        return str(o)


def getPaperPageVersion(tpv: str) -> str:
    """Return the paper, page, version substring of a TPV string.

    Args:
        tpv: a TPV string of the form "TTTTTPPPVVOCCCCCC",
            typically from a QR-code

    Returns:
        A substring of the original TPV string,
        containing the paper number, page number and version number.
    """
    return tpv[0:10]


def parse_paper_page_version(ppv: str) -> tuple[int, int, int]:
    """Parse string "TTTTTPPPVV" into paper-number, page-number, version triple.

    Args:
        ppv: a string of the form "TTTTTPPPVV".

    Returns:
        A triple of integers,
        tn: paper number, up to 5 digits (formally "test number"),
        pn: page group number, up to 3 digits, and
        vn: version number, up to 2 digits.
    """
    assert len(ppv) == len("TTTTTPPPVV")
    return (
        int(ppv[:5]),
        int(ppv[5:8]),
        int(ppv[8:10]),
    )


def getPosition(tpv: str) -> int:
    """Return the orientation/position code, which corner the QR code should be located."""
    return int(parseTPV(tpv)[4])


def getCode(tpv: str) -> str:
    """Return the magic code from a TPV string."""
    return parseTPV(tpv)[3]


def encodePaperPageVersion(papernum: str | int, p: str | int, v: str | int) -> str:
    """Encode three values as the short paper-page-version code.

    Typically used for collision detection.

    Args:
        papernum: satisfying 0 ≤ papernum ≤ 99999
        p: page number, 1 ≤ p ≤ 999
        v: version number, 1 ≤
    v ≤ 99

    Returns:
        A string of the short page-paper-version code
    """
    assert int(papernum) >= 0
    # TODO: allow zero
    assert int(v) >= 1
    assert int(p) >= 1
    papernum = str(papernum).zfill(5)
    p = str(p).zfill(3)
    v = str(v).zfill(2)
    assert papernum.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert len(papernum) == 5
    assert len(p) == 3
    assert len(v) == 2
    tpv = f"{papernum}{p}{v}"
    assert len(tpv) == 10
    return tpv


def encodeTPV(
    papernum: int | str, p: int | str, v: int | str, o: int | str, code: int | str
) -> str:
    """Encode some values as a TPV code.

    Args:
        papernum: satisfying 0 ≤ papernum ≤ 99999
        p: page number, 1 ≤ p ≤ 990
        v: version number, 1 ≤ v ≤ 99
        o: position code, 0 ≤ code ≤ 4
        code: magic code, 0 ≤ code ≤ 999999

    Returns:
        A string of the full TPV code.
    """
    assert int(papernum) >= 0
    # TODO: allow zero
    assert int(v) >= 1
    assert int(p) >= 1
    assert int(o) >= 0 and int(o) <= 4
    papernum = str(papernum).zfill(5)
    p = str(p).zfill(3)
    v = str(v).zfill(2)
    o = str(o)
    code = str(code).zfill(6)
    assert papernum.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert o.isnumeric()
    assert code.isnumeric()
    assert len(papernum) == 5
    assert len(p) == 3
    assert len(v) == 2
    assert len(o) == 1
    assert len(code) == 6
    tpv = f"{papernum}{p}{v}{o}{code}"
    assert len(tpv) == 17
    return tpv


def new_magic_code(seed=None) -> str:
    """Generate a new random magic code.

    Args:
        seed: seed for the random number generator, or ``None`` for
            something reasonable (i.e., current time).

    Returns:
        The magic code, a 6-digit string of digits.
    """
    random.seed(seed)
    magic = str(random.randrange(0, 10**6)).zfill(6)
    assert len(magic) == 6
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


def isValidBundleSeparatorPaperCode(code: str) -> bool:
    """Is this a valid Plom-bundle-separator-paper code?

    Args:
        code: a string to check.

    Returns:
        The validity of the bundle separator page code.
    """
    code = code.lstrip("plomB")
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
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom scrap page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomS{orientation}"


def encodeBundleSeparatorPaperCode(orientation: str | int) -> str:
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom bundle separator page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomB{orientation}"


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


def getBundleSeparatorPaperOrientation(code: str) -> int:
    """Extra the orientation digit from a valid Plom bundle-separator-paper code.

    Args:
        code: a Plom bundle-separator-paper code.

    Returns:
        The orientation as a small integer.
    """
    return int(code[5])
