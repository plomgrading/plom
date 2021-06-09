# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer

"""Utilities for dealing with TPV codes

A TPV code is a string of 17 digits of the form

  EETTTTPPVVOCCCCCC
  01234567890123456

This is as much as can be packed into a QR code without
increasing its size.

The format consists of:
  * 01 = API
  * 2345 = test number
  * 67 = page number
  * 89 = version
  * 0 = position/orientation code
  * 123456 = magic code

A TPV code can be optionally prefixed with "QR-Code:"

  QR-Code:EETTTTPPVVOCCCCCC

Orientation code:
  * 0 no position information (reserved, unused)
  * 1 NE
  * 2 NW
  * 3 SW
  * 4 SE
  * 5-9 (currently unused)

TODO: might encapsulate position code, have ``getPosition`` return
e.g., the string `"NE"`
"""

import random


# Changes to this format should bump this.  Possibly changes
# to the layout of QR codes on the page should too.
_API = "00"


def isValidTPV(tpv):
    """Is this a valid TPV code?"""
    tpv = tpv.lstrip("QR-Code:")
    if len(tpv) != len("EETTTTPPVVOCCCCCC"):
        return False
    return tpv.isnumeric()


def parseTPV(tpv):
    """Parse a TPV string (typically from a QR-code)

    Args: tpv (str): a TPV string of the form "EETTTTPPVVOCCCCCC",
       typically from a QR-code, possibly with the prefix "QR-Code:".

    Returns:
       tn (int): test number, up to 4 digits
       pn (int): page group number, up to 2 digits
       vn (int): version number, up to 2 digits
       en (str): the API number, 2 digits zero padded
       cn (str): the "magic code", 6 digits zero padded
       o (str): the orientation code, TODO
    """
    tpv = tpv.lstrip("QR-Code:")
    # en = tpv[0:2]
    tn = int(tpv[2:6])
    pn = int(tpv[6:8])
    vn = int(tpv[8:10])
    o = tpv[10]
    cn = tpv[11:]
    return tn, pn, vn, cn, o


def getPosition(tpv):
    return int(parseTPV(tpv)[4])


def getAPI(tpv):
    tpv = tpv.lstrip("QR-Code:")
    return tpv[0:2]


def hasCurrentAPI(tpv):
    """does tpv have the current API?

    Args: tpv (str): a TPV string of the form "EETTTTPPVVOCCCCCC",
       typically from a QR-code.
    """
    return getAPI(tpv) == _API


def getCode(tpv):
    """return the magic code for tpv

    Args: tpv (str): a TPV string.
    """
    return parseTPV(tpv)[3]


def encodeTPV(test, p, v, o, code):
    """Encode some values as a TPV code

    Args:
       test (int/str): the test number, 1 ≤ test ≤ 9999
       p (int/str): page number, 1 ≤ p ≤ 99
       v (int/str): version number, 1 ≤ v ≤ 99
       o (int/str): position code, 0 ≤ code ≤ 4
       code (int/str): magic code, 0 ≤ code ≤ 999999

    Returns:
       str: the tpv code
    """
    assert int(test) >= 1
    assert int(v) >= 1
    assert int(p) >= 1
    assert int(o) >= 0 and int(o) <= 4
    test = str(test).zfill(4)
    p = str(p).zfill(2)
    v = str(v).zfill(2)
    o = str(o)
    code = str(code).zfill(6)
    assert test.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert o.isnumeric()
    assert code.isnumeric()
    assert len(test) == 4
    assert len(p) == 2
    assert len(v) == 2
    assert len(o) == 1
    assert len(code) == 6
    tpv = "{}{}{}{}{}{}".format(_API, test, p, v, o, code)
    assert len(tpv) == 17
    return tpv


def newMagicCode(seed=None):
    """Generate a new random magic code"

    Args:
       seed: seed for the random number generator, or ``None`` for
             something reasonable (i.e.., current time).

    Returns:
       str: the magic code
    """
    random.seed(seed)
    magic = str(random.randrange(0, 10 ** 6)).zfill(6)
    assert len(magic) == 6
    return magic
