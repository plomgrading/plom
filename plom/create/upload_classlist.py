# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from plom.plom_exceptions import (
    PlomConflict,
    PlomRangeException,
)
from plom.create import with_manager_messenger
from plom.rules import censorStudentName, censorStudentID
from .buildClasslist import get_demo_classlist


@with_manager_messenger
def upload_classlist(classlist, *, msgr, force=False):
    """Uploads a classlist file to the server.

    Arg:
        classdict (list): list of dict, each has at least keys `"id"` and
            `"name"`, optionally other fields too.

    Keyword Arg:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        force (bool): Force uploading if a classlist already exists,
            default `False`.

    Returns:
        None
    """
    _ultra_raw_upload_classlist(classlist, msgr, force=force)


def _raw_upload_classlist(classlist, msgr):
    # TODO: does this distinct only exist for the mock test?  Maybe not worth it!
    try:
        _ultra_raw_upload_classlist(classlist, msgr)
    finally:
        msgr.closeUser()
        msgr.stop()


def _ultra_raw_upload_classlist(classlist, msgr, *, force=False):
    # TODO: clean up this chain viz the mock test
    try:
        msgr.upload_classlist(classlist, force)
        print(f"Uploaded classlist of length {len(classlist)}.")
        print(
            "  First student:  {} - {}".format(
                censorStudentID(classlist[0]["id"]),
                censorStudentName(classlist[0]["name"]),
            )
        )
        print(
            "  Last student:  {} - {}".format(
                censorStudentID(classlist[-1]["id"]),
                censorStudentName(classlist[-1]["name"]),
            )
        )
    except PlomRangeException as e:
        print(
            "Error: classlist lead to the following specification error:\n"
            "  {}\n"
            "Perhaps classlist is too large for specTest.numberToProduce?".format(e)
        )
        raise
    except PlomConflict:
        print("Error: Server already has a classlist, see help.")
        raise


@with_manager_messenger
def upload_demo_classlist(spec, *, msgr, force=False):
    """Uploads the demo classlist file to the server.

    Args:
        spec: the server assessment specification.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        force (bool): Force uploading if a classlist already exists,
            default `False`.

    Returns:
        None
    """
    print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
    classlist = get_demo_classlist(spec)

    _ultra_raw_upload_classlist(classlist, msgr, force=force)
