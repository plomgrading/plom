#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2018-2019 Colin B. Macdonald <cbm@m.fsf.org>
#
# This file is part of Plom.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import hashlib

# If you know the salt string and you know someone's student
# number, you can determine their code.  You should set this
# per course (not per test).  TODO: move into the spec file?
SALTSTR = "salt"


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
