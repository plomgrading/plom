# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Colin B. Macdonald

"""Utils concerning rules about data, like valid student numbers."""


StudentIDLength = 8


def isValidUBCStudentNumber(n):
    """Is this a valid student number for UBC?

    Input must be a string or string like or convertible by str().
    """
    try:
        sid = int(str(n))
    except:  # noqa: E722
        return False
    if sid < 0:
        return False
    if len(str(n)) != StudentIDLength:
        return False
    return True


def is_z_padded_integer(n):
    """Is this string a z-padded int

    Input must be a string that when z's (or Z's) are removed gives a non-negative integer. We may require this for debugging with 'fake' student numbers which are constructed from some other id by padding with z's. Must have correct length - as per StudentIDLength
    """
    de_z = n.replace("z", "0").replace("Z", "0")
    if len(de_z) != StudentIDLength:
        return False
    try:
        sid = int(str(de_z))
    except:  # noqa: E722
        return False
    if sid < 0:
        return False

    return True


def censorStudentNumber(n):
    """Replace some parts of student number with astericks."""
    n = str(n)
    r = n[:2] + "****" + n[-2:]
    assert len(n) == len(r)
    return r


def censorStudentName(s):
    """Replace most of a student student name with astericks."""
    if len(s) <= 3:
        r = s[0] + "*" * 7
    else:
        r = s[:3] + "*" * 5
    return r


def isValidStudentNumber(n):
    """Check if is either a valid UBC SID or a z-padded int of correct length."""

    return isValidUBCStudentNumber(n) or is_z_padded_integer(n)
