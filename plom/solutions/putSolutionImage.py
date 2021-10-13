# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

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
            'In order to force-logout the existing authorisation run "plom-solutions clear"'
        )
        raise

    try:
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

        msgr.putSolutionImage(question, version, imageName)
        return [True, f"Solution for {question}.{version} uploaded"]

    finally:
        msgr.closeUser()
        msgr.stop()


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
            'In order to force-logout the existing authorisation run "plom-solutions clear"'
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
