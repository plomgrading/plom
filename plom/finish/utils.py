# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2019 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

"""Misc utilities"""

import secrets
import hashlib


def my_hash(s, salt=None):
    """Hash a string to a 12-digit code

    Combine the string with a salt string, compute the md5sum, grab
    the first few digits as an integer between 100000000000 and 999999999999.

    Args:
        s (str): string to hash.
        salt (str, optional): Salt string for the hash. Defaults to None (but will raise an error). https://en.wikipedia.org/wiki/Salt_(cryptography)

    Raises:
        ValueError -- if the given value for salt is None.

    Returns:
        str -- The hashed (and salted string) string.
    """
    if not salt:
        raise ValueError("You must set the Salt String")
    hashthis = s + salt
    h = hashlib.md5(hashthis.encode("utf-8")).hexdigest()
    b = 899_999_999_999
    l = 100_000_000_000
    return str(int(h, 16) % b + l)


def my_secret():
    """Proper random 12-digit code (between 100_000_000_000 and 999_999_999_999).

    Returns:
        int: random code.
    """
    b = 900_000_000_000
    l = 100_000_000_000
    return secrets.randbelow(b) + l
