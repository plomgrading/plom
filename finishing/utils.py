# -*- coding: utf-8 -*-

"""Misc utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib

# If you know the salt string and you know someone's student
# number, you can determine their code.  You should set this
# per course (not per test).  TODO: move into the spec file?
SALTSTR = "default"


def myhash(s, salt=None):
    """
    Hash a string to a 12-digit code

    Combine the string with a salt string, compute the md5sum, grab
    the first few digits as an integer between 100000000000 and 999999999999.
    """
    salt = SALTSTR if salt is None else salt
    hashthis = s + salt
    h = hashlib.md5(hashthis.encode("utf-8")).hexdigest()
    b = 899_999_999_999
    l = 100_000_000_000
    return str(int(h, 16) % b + l)


def test_hash():
    assert myhash("12345678", salt="salt") == "351525727036"
    assert myhash("12345678", salt="salty") == "782385405730"
    assert myhash("12345679", salt="salt") == "909470548567"
