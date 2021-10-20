# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import (
    PlomExistingLoginException,
    PlomConflict,
    PlomRangeException,
)
from plom.rules import censorStudentName, censorStudentNumber
from .buildClasslist import get_demo_classlist


def get_messenger(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)

    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        # TODO: bit annoying, maybe want manager UI open...
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another management tool running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-build clear"'
        )
        raise

    return msgr


def upload_classlist(classlist, server, password):
    """Uploads a classlist file to the server.

    Arguments:
        classdict (list): list of dict, each has at least keys `"id"` and
            `"studentName"`, optionally other fields too.
        msgr (ManagerMessenger): an already-connected messenger object for
            talking to the server.
    """
    msgr = get_messenger(server, password)
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
