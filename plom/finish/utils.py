# -*- coding: utf-8 -*-

"""Misc utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2020 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib


def myhash(s, salt=None):
    """
    Hash a string to a 12-digit code

    Combine the string with a salt string, compute the md5sum, grab
    the first few digits as an integer between 100000000000 and 999999999999.
    """
    if not salt:
        raise ValueError("You must set the Salt String")
    hashthis = s + salt
    h = hashlib.md5(hashthis.encode("utf-8")).hexdigest()
    b = 899_999_999_999
    l = 100_000_000_000
    return str(int(h, 16) % b + l)
