# -*- coding: utf-8 -*-

"""Utils Misc utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import math

def isValidUBCStudentNumber(n):
    """Is this a valid student number for UBC?"""
    try:
        sid = int(str(n))
    except:
        return False
    if sid < 0:
        return False
    if len(str(n)) != 8:
        return False
    return True

isValidStudentNumber = isValidUBCStudentNumber
