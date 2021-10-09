# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException

solution_path = Path("solutionImages")


def putSolutionImage(
    question,
    version,
    imageName,
    server=None,
    password=None,
):
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
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        raise

    spec = msgr.get_spec()
    # nb question,version are strings at this point
    iq = int(question)
    iv = int(version)
    if iq < 1 or iq > spec["numberOfQuestions"]:
        return [False, "Question number out of range"]
    if iv < 1 or iv > spec["numberOfVersions"]:
        return [False, "Version number out of range"]
    if spec["question"][question]["select"] == "fix" and iv != 1:
        return [False, f"Question{question} has fixed version = 1"]

    try:
        msgr.putSolutionImage(question, version, imageName)
    finally:
        msgr.closeUser()
        msgr.stop()

    return [True, f"Solution for {question}.{version} uploaded"]


def putExtractedSolutionImages(server=None, password=None):
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
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        raise

    try:
        spec = msgr.get_spec()
        # nb question,version are strings at this point
        for q in range(1, spec["numberOfQuestions"] + 1):
            mxv = spec["numberOfVersions"]
            if spec["question"][str(q)]["select"] == "fix":
                mxv = 1  # only do version 1 if 'fix'
            for v in range(1, mxv + 1):
                image_name = solution_path / f"solution.q{q}.v{v}.png"
                msgr.putSolutionImage(q, v, image_name)

    finally:
        msgr.closeUser()
        msgr.stop()
