# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

"""Randomly ID papers for testing purposes."""

import random

from plom.plom_exceptions import (
    PlomConflict,
    PlomExistingLoginException,
    PlomTakenException,
)
from plom.messenger import Messenger


def do_rando_identifying_backend(messenger):
    classlist = messenger.IDrequestClasslist()
    # classlist is a list of dicts {'id': sid, 'name: name}
    predictions = messenger.IDgetPredictionsFromPredictor("prename")
    # due to jsonnery the key test_number is a string (sigh).

    # make sid to name look up for prenames
    sid_to_name = {X["id"]: X["name"] for X in classlist}
    # and a sid to test look up
    sid_to_test = {predictions[X]["student_id"]: X for X in predictions}

    while True:
        task = messenger.IDaskNextTask()
        if task is None:
            print("No more tasks.")
            break
        try:
            print("Identifying task ", task)
            messenger.IDclaimThisTask(task)
        except PlomTakenException:
            # task already taken.
            continue

        # where possible take the prenamed ID
        if str(task) in predictions:
            sid = predictions[str(task)]["student_id"]
            name = sid_to_name[sid]
            print(f"Task {task} prenamed to be {sid} {name} - using that")
            try:
                messenger.IDreturnIDdTask(task, sid, name)
            except PlomConflict:
                print(f"Already used: {name}")
        else:
            # otherwise pull one randomly from the classlist
            # but not one that is used for a prediction.
            while True:
                try:
                    person = random.choice(classlist)
                    if person["id"] not in sid_to_test:
                        name = person["name"] + " [randomly chosen]"
                        messenger.IDreturnIDdTask(task, person["id"], name)
                        break
                except PlomConflict:
                    print(f"Already used: {person}")


def do_rando_identifying(server, user, password):
    """Randomly associate papers with students: only for testing please.

    args:
        server (str)
        user (str)
        password (str)

    returns:
        int: 0 on success, non-zero on error/unexpected.
    """
    if server and ":" in server:
        s, p = server.split(":")
        messenger = Messenger(s, port=p)
    else:
        messenger = Messenger(server)
    messenger.start()

    try:
        messenger.requestAndSaveToken(user, password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "This script has automatically force-logout'd that user."
        )
        messenger.clearAuthorisation(user, password)
        return 1

    try:
        do_rando_identifying_backend(messenger)
    finally:
        messenger.closeUser()
        messenger.stop()
    return 0
