"""Utilities for dealing with TGV codes

A TGV code is a string of 17 digits of the form

  TTTTPPVVEECCCCCCC
  01234567890123456

This is as much as can be packed into a QR code without
increasing its size.

The format consists of:
  * 0123 = test number
  * 45 = page number
  * 67 = version
  * 89 = API
  * 0123456 = magic code
"""

__author__ = "Colin Macdonald"
__copyright__ = "Copyright (C) 2019 Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"


# Changes to this format should bump this.  Possibly changes
# to the layout of QR codes on the page should too.
_API = "01"


def isValidTGV(tgv):
    """Is the input a valid TGV+ code?
    """
    if len(tgv) != len("TTTTPPVVEECCCCCCC"):
        return False
    return qr.isnumeric()


def isQRCodeWithValidTGV(qr):
    """Valid lines are "QR-Code:TTTTPPVVEECCCCCCC"
    """
    if not qr.startswith("QR-Code:"):
        return False
    return isValidTGV(qr[9:])


def parseTGV(tgv):
    """Parse a TGV+ string (typically from a QR-code)

    Args: tgv (str): a TGV+ code of the form "TTTTPPVVEECCCCCCC",
       typically from a QR-code, with the prefix "QR-Code:" stripped.

    Returns:
       tn (int): test number, up to 4 digits
       pn (int): page group number, up to 2 digits
       vn (int): version number, up to 2 digits
       en (str): the API number, 2 digits zero padded
       cn (str): the "magic code", 7 digits zero padded
    """
    tn = int(tgv[0:4])
    pn = int(tgv[4:6])
    vn = int(tgv[6:8])
    en = tgv[8:10]
    cn = tgv[10:]
    return tn, pn, vn, en, cn


def encodeTGV(test, p, v, code):
    """Encode some values as a TGV code

    Args:
       test (int/str): the test number, 1 ≤ test ≤ 9999
       p (int/str): page number, 1 ≤ p ≤ 99
       v (int/str): version number, 1 ≤ v ≤ 99
       code (int/str): magic code, 0 ≤ code ≤ 9999999

    Returns:
       str: the tgv code
    """
    assert int(test) >= 1
    assert int(v) >= 1
    assert int(p) >= 1
    test = str(test).zfill(4)
    p = str(p).zfill(2)
    v = str(v).zfill(2)
    code = str(code).zfill(7)
    assert test.isnumeric()
    assert p.isnumeric()
    assert v.isnumeric()
    assert code.isnumeric()
    assert len(test) == 4
    assert len(p) == 2
    assert len(v) == 2
    assert len(code) == 7
    tgv = "{}{}{}{}{}".format(test, p, v, _API, code)
    assert len(tgv) == 17
    return tgv


def newMagicCode(seed=None):
    """Generate a new random magic code"

    Args:
       seed: seed for the random number generator, or ``None`` for
             something reasonable (i.e.., current time).

    Returns:
       str: the magic code
    """
    random.seed(seed)
    magic = str(random.randrange(0, 10**7)).zfill(7)
    assert len(magic) == 7
    return magic
