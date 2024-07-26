# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021-2024 Andrew Rechnitzer
# Copyright (C) 2023 Philip Loewen
# Copyright (C) 2024 Aden Chan

"""Utils concerning rules about data, like valid student numbers."""

StudentIDLength = 8


def testValidUBCStudentID(n):
    """Check if input is a valid student number for UBC and an explanation.

    Input must be a string or string like or convertible by str().
    """
    if len(str(n)) == 0:  # for 3091 - explicit error for blank ID.
        return (False, "SID is blank")
    try:
        sid = int(str(n))
    except:  # noqa: E722
        return (False, f"SID '{n}' is not an integer")
    if sid < 0:
        return (False, f"SID '{n}' is negative")
    if len(str(n)) != StudentIDLength:
        return (
            False,
            f"SID '{n}' has incorrect length - expecting {StudentIDLength} digits",
        )
    return (True, "")


def isValidUBCStudentID(n):
    """Is this a valid student number for UBC?"""
    ok, _ = testValidUBCStudentID(n)
    return ok


def test_z_padded_integer(n):
    """Is this string a z-padded integer, and an explanation.

    Input must be a string that when z's (or Z's) are removed gives a non-negative integer. We may require this for debugging with 'fake' student numbers which are constructed from some other id by padding with z's. Must have correct length - as per StudentIDLength
    """
    de_z = n.replace("z", "0").replace("Z", "0")
    if len(de_z) != StudentIDLength:
        return (
            False,
            f"SID {n} has incorrect length - expecting {StudentIDLength} digits",
        )
    try:
        sid = int(str(de_z))
    except:  # noqa: E722
        return (False, f"SID {n} is not a z-padded integer")
    if sid < 0:
        return (False, f"SID {n} is a negative z-padded integer")

    return (True, "")


def is_z_padded_integer(n):
    """Is this string a z-padded integer?"""
    ok, _ = test_z_padded_integer(n)
    return ok


def censorStudentID(n):
    """Replace some parts of student number with asterisks.

    If it doesn't look like a student number, we don't censor it.
    """
    n = str(n)
    if not is_z_padded_integer(n):
        return n
    r = n[:2] + "****" + n[-2:]
    assert len(n) == len(r)
    return r


def censorStudentName(s):
    """Replace most of a student name with asterisks."""
    if len(s) <= 3:
        r = s[0] + "*" * 7
    else:
        r = s[:3] + "*" * 5
    return r


def validateStudentID(n):
    """Check if is either a valid UBC SID or a z-padded int of correct length, and return any errors."""
    s, msg1 = testValidUBCStudentID(n)
    if s:
        # is valid UBC SID.
        return s, msg1
    else:  # Could still be z-padded int
        s, msg2 = test_z_padded_integer(n)
        if s:
            return (s, msg1)
        else:
            return (s, msg1 + ", " + msg2)


def isValidStudentID(n):
    """Check if is either a valid UBC SID or a z-padded int of correct length. Ignores any error messages."""
    return isValidUBCStudentID(n) or is_z_padded_integer(n)
