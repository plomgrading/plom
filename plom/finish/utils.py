# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020, 2023-2024 Colin B. Macdonald
# Copyright (C) 2019 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

"""Misc utilities."""

import secrets
import hashlib


def salted_int_hash_from_str(s, salt=None, digits=9):
    """Hash a string to a 9-digit code.

    Combine the string with a salt string, compute the md5sum, grab
    the first few digits as an integer between 100000000 and 999999999.
    Reference: https://en.wikipedia.org/wiki/Salt_(cryptography)

    Args:
        s (str): string to hash.
        salt (str, optional): Salt string for the hash. Defaults to None
        (but will raise an error).
        digits (int): how many digits, defaults to 9.

    Raises:
        ValueError: the given value for salt is None.

    Returns:
        str: The hashed and salted string.
    """
    MAXDIGITS = 38
    if not salt:
        raise ValueError("You must set the Salt String")
    if digits < 2:
        raise ValueError("Not enough digits")
    if digits > MAXDIGITS:
        raise NotImplementedError(
            "This implementation maxes out at {} digits".format(MAXDIGITS)
        )
    hashthis = s + salt
    h = hashlib.md5(hashthis.encode("utf-8")).hexdigest()
    if digits == 12:
        # SPECIAL CASE for backwards compat
        b = 899_999_999_999
        low = 100_000_000_000
        return str(int(h, 16) % b + low)
    b = 9 * 10 ** (digits - 1)
    low = 10 ** (digits - 1)
    return str(int(h, 16) % b + low)


def salted_hex_hash_from_str(s, salt=None, digits=16):
    """Hash a string to a hexdigit code with salt.

    Combine the string with a salt string, compute the a secure hash,
    grab the first few hexadecimal digits.

    Args:
        s (str): string to hash.
        salt (str, optional): Salt string for the hash. Defaults to None
            which will raise an error.
        digits (int): how many digits, defaults to 16.

    Raises:
        ValueError: the given value for salt is None.

    Returns:
        str: The hashed and salted string.
    """
    MAXDIGITS = 128
    if not salt:
        raise ValueError("You must set the Salt String")
    if digits < 2:
        raise ValueError("Not enough digits")
    if digits > MAXDIGITS:
        raise NotImplementedError(
            "This implementation maxes out at {} digits".format(MAXDIGITS)
        )
    hashthis = s + salt
    h = hashlib.sha256(hashthis.encode("utf-8")).hexdigest()
    return h[0:digits]


def rand_integer_code(digits=9):
    """Proper random 9-digit code (between 100_000_000 and 999_999_999).

    Args:
        digits (int): defaults to 9.

    Returns:
        int: random code.
    """
    b = 9 * 10 ** (digits - 1)
    low = 10 ** (digits - 1)
    return secrets.randbelow(b) + low


def rand_hex(digits=16):
    """Proper random hex string."""
    return secrets.token_hex((digits + 1) // 2)[0:digits]
