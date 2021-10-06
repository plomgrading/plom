# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


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

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        raise

    spec = msgr.get_spec()
    if question < 1 or question > spec["numberOfQuestions"]:
        return [False, "Question number out of range"]
    if version < 1 or version > spec["numberOfVersions"]:
        return [False, "Version number out of range"]
    if spec["question"][question].select == "fixed" and version != 1:
        return [False, f"Question{question} has fixed version = 1"]

    try:
        msgr.putSolutionImage(question, version, imageName)
    finally:
        msgr.closeUser()
        msgr.stop()

    return [True, f"Solution for {question}.{version} uploaded"]
