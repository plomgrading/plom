# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020, 2022 Colin B. Macdonald
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

Also handles plom extra page codes. These are alphanumeric stored in micro-qr codes
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

Also handles plom scrap-paper codes. These are alphanumeric stored in micro-qr codes
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

import random


def isValidTPV(tpv):
    """Is this a valid TPV code?

    Note that the pyzbar module gives codes with the prefix 'QR-Code:',
    however the zxing-cpp module does not.
    """
    # string prefix is needed for pyzbar but not zxingcpp
    tpv = tpv.lstrip("QR-Code:")
    if len(tpv) != len("TTTTTPPPVVVOCCCCC"):  # todo = remove in future.
        return False
    return tpv.isnumeric()


def isValidExtraPage(tpv):
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


def parseTPV(tpv):
    """Parse a TPV string (typically from a QR-code).

    Args: tpv (str): a TPV string of the form "TTTTTPPPVVVOCCCCC",
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


def parseExtraPageCode(expc):
    """Parse an extra page code string (typically from a QR-code).

    Args: expc (str): an extra page code string of the form "plomXO",
       typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
       o (str): the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    expc = expc.lstrip("QR-Code:")  # todo = remove in future.
    o = int(expc[5])
    if o > 4:
        return str(o - 4)  # todo - keep the 5-8 possibilities
    else:
        return str(o)


def parseScrapPaperCode(scpc):
    """Parse an scrap-paper code string (typically from a QR-code).

    Args: scpc (str): a scrap-paper code string of the form "plomSO",
       typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
       o (str): the orientation code, TODO
    """
    # strip prefix is needed for pyzbar but not zxingcpp
    scpc = scpc.lstrip("QR-Code:")  # todo = remove in future.
    o = int(scpc[5])
    if o > 4:
        return str(o - 4)  # todo - keep the 5-8 possibilities
    else:
        return str(o)


def getPaperPageVersion(tpv):
    """Return the paper, page, version substring of a TPV string.

    Args: tpv (str): a TPV string of the form "TTTTTPPPVVVOCCCCC",
       typically from a QR-code

    Returns:
       (str): a substring of the original TPV string,
       containing the paper number, page number and version number.
    """
    return tpv[0:11]


def parse_paper_page_version(ppv_key):
    """Parse the paper-page-version string "TTTTTPPPVVV" and return a
    triple of the the paper-number, page-number and version.

    Args:  (str): a string of the form "TTTTTPPPVVV"

    Returns:
       tn (int): test number, up to 5 digits
       pn (int): page group number, up to 3 digits
       vn (int): version number, up to 3 digits
    """
    assert len(ppv_key) == len("TTTTTPPPVVV")
    return (
        int(ppv_key[:5]),
        int(ppv_key[5:8]),
        int(ppv_key[8:11]),
    )


def getPosition(tpv):
    return int(parseTPV(tpv)[4])


def getCode(tpv):
    """Return the magic code for tpv.

    Args: tpv (str): a TPV string.
    """
    return parseTPV(tpv)[3]


def encodePaperPageVersion(paper_number, p, v):
    """Encode some values as the short paper-page-version code - used
    typically for collision detection.

    Args:
       test (int/str): the test number, 1 ≤ test ≤ 99999
       p (int/str): page number, 1 ≤ p ≤ 990
       v (int/str): version number, 1 ≤ v ≤ 909

    Returns:
       str: the short page-paper-version code
    """
    assert int(paper_number) >= 1
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


def encodeTPV(test, p, v, o, code):
    """Encode some values as a TPV code.

    Args:
       test (int/str): the test number, 1 ≤ test ≤ 99999
       p (int/str): page number, 1 ≤ p ≤ 990
       v (int/str): version number, 1 ≤ v ≤ 909
       o (int/str): position code, 0 ≤ code ≤ 4
       code (int/str): magic code, 0 ≤ code ≤ 99999

    Returns:
       str: the tpv code
    """
    assert int(test) >= 1
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


def new_magic_code(seed=None):
    """Generate a new random magic code.

    Args:
       seed: seed for the random number generator, or ``None`` for
             something reasonable (i.e.., current time).

    Returns:
       str: the magic code
    """
    random.seed(seed)
    magic = str(random.randrange(0, 10**5)).zfill(5)
    assert len(magic) == 5
    return magic


def isValidExtraPageCode(code):
    """Is this a valid plom-extra-page code?

    Args:
       code (str): a plom extra page code

    Returns:
       bool: the validity of the extra page code.

    """
    code = code.lstrip("plomX")
    if len(code) != len("O"):
        return False
    # now check that remaining letter is a digit in 1,2,..,8.
    if code.isnumeric():
        if 1 <= int(code) <= 8:
            return True
    return False


def isValidScrapPaperCode(code):
    """Is this a valid plom-scrap-paper code?

    Args:
       code (str): a plom extra page code

    Returns:
       bool: the validity of the extra page code.

    """
    code = code.lstrip("plomS")
    if len(code) != len("O"):
        return False
    # now check that remaining letter is a digit in 1,2,..,8.
    if code.isnumeric():
        if 1 <= int(code) <= 8:
            return True
    return False


def encodeExtraPageCode(orientation):
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom extra page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomX{orientation}"


def encodeScrapPaperCode(orientation):
    """Take an orientation (1 <= orientation <= 8) and turn it into a plom extra page code."""
    assert int(orientation) >= 1 and int(orientation) <= 8
    return f"plomS{orientation}"


def getExtraPageOrientation(code):
    """Extra the orientation digit from a valid plom extra page code.

    Args:
       code (str): a plom extra page code

    Returns:
       int: the orientation
    """
    return int(code[5])


def getScrapPaperOrientation(code):
    """Extra the orientation digit from a valid plom scrap-paper code.

    Args:
       code (str): a plom scrap-paper code

    Returns:
       int: the orientation
    """
    return int(code[5])
