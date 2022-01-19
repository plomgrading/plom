# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

import json

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish import RubricListFilename, TestRubricMatrixFilename


def download_rubric_files(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorization run `plom-finish clear`."
        )
        raise

    try:
        counts = msgr.RgetRubricCounts()
        tr_matrix = msgr.RgetTestRubricMatrix()

    finally:
        msgr.closeUser()
        msgr.stop()

    # counts is a dict indexed by key - turn it into a list
    # this makes it compatible with plom-create rubric upload
    rubric_list = [Y for X, Y in counts.items()]

    with open(RubricListFilename, "w") as fh:
        json.dump(rubric_list, fh, indent="  ")

    with open(TestRubricMatrixFilename, "w") as fh:
        json.dump(tr_matrix, fh)


def main(server=None, password=None):
    download_rubric_files(server, password)
