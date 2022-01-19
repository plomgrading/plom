# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from plom.plom_exceptions import (
    PlomConflict,
    PlomRangeException,
)
from plom.create import start_messenger
from plom.rules import censorStudentName, censorStudentNumber
from .buildClasslist import get_demo_classlist


def upload_classlist(classlist, server, password):
    """Uploads a classlist file to the server.

    Arguments:
        classdict (list): list of dict, each has at least keys `"id"` and
            `"studentName"`, optionally other fields too.
        msgr (ManagerMessenger): an already-connected messenger object for
            talking to the server.
    """
    msgr = start_messenger(server, password)
    _raw_upload_classlist(classlist, msgr)


def _raw_upload_classlist(classlist, msgr):
    # TODO: does this distinct only exist for the mock test?  Maybe not worth it!
    try:
        msgr.upload_classlist(classlist)
        print(f"Uploaded classlist of length {len(classlist)}.")
        print(
            "  First student:  {} - {}".format(
                censorStudentNumber(classlist[0]["id"]),
                censorStudentName(classlist[0]["studentName"]),
            )
        )
        print(
            "  Last student:  {} - {}".format(
                censorStudentNumber(classlist[-1]["id"]),
                censorStudentName(classlist[-1]["studentName"]),
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
        print("Error: Server already has a classlist, see help (TODO: add force?).")
        raise
    finally:
        msgr.closeUser()
        msgr.stop()


def upload_demo_classlist(server=None, password=None):
    """Uploads the demo classlist file to the server."""

    print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
    classlist = get_demo_classlist()
    upload_classlist(classlist, server, password)
