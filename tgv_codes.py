__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

from collections import defaultdict
import glob
import json
import os
import re
import shutil
import sys


# to make sure data in the qr code is formatted the way we think
# TTTTPPVVEECCCCCCC is version 01 and EE=01
# 17 digits is as much as can be packed into this size qr.
# beyond that the qr needs to be more dense.
_DataInQrFormatVersion_ = "01"


def isQRCodeWithValidTGV(qr):
    """
    Valid lines are "QR-Code:TTTTPPVVEECCCCCCC"
    i.e., 17 digits in the form:
    0123 = Test number, 45 = page number, 67 = version, 89 = API, 0123456 = code"""
    if len(qr) != len("QR-Code:TTTTPPVVEECCCCCCC"):
        return False
    if not qr.startswith("QR-Code:"):
        return False
    # tail must be numeric
    return qr[9:].isnumeric()


def parseTGV(tgv):
    """Parse a TGV+ string (typically from a QR-code)

    Args: tgv (str): a TGV+ code, typically from a QR-code, with the
       prefix "QR-Code:" stripped.

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

    TODO: should this assert the constraints are satified?

    Args:
       test (int): the test number
       p (int): page group number
       v (int): version number
       code (str): magic code (should this be an int or string?)

    Returns:
       tgv (str)
    """
    tgv = "{}{}{}{}{}".format(
        str(test).zfill(4),
        str(p).zfill(2),
        str(v).zfill(2),
        _DataInQrFormatVersion_,
        code,
    )
