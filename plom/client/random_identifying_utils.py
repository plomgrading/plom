# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

"""Randomly ID papers for testing purposes."""

import random
from typing import Union

from plom.messenger import Messenger
from plom.plom_exceptions import (
    PlomConflict,
    PlomExistingLoginException,
    PlomTakenException,
)


def do_rando_identifying_backend(
    messenger,
    *,
    use_predictions: bool = False,
) -> None:
    classlist = messenger.IDrequestClasslist()
    # classlist is a list of dicts {'id': sid, 'name: name}
    prenames = messenger.IDgetPredictionsFromPredictor("prename")
    if use_predictions:
        mllap = messenger.IDgetPredictionsFromPredictor("MLLAP")
        mlgreedy = messenger.IDgetPredictionsFromPredictor("MLGreedy")
        # use the higher-certainty prediction from these
        ml_predictions = {X: mllap[X] for X in mllap if mllap[X]["certainty"] >= 0.1}
        for X, dat in mlgreedy.items():
            if dat["certainty"] < 0.1:
                continue  # if low certainty, ignore it.
            if X not in ml_predictions:  # don't have a prediction, so use it
                ml_predictions[X] = dat
            else:
                # existing prediction so keep one with higher certainty
                if ml_predictions[X]["certainty"] < dat["certainty"]:
                    ml_predictions[X] = dat
    # due to jsonnery the key test_number is a string (sigh).

    # make sid to name look up for prenames
    sid_to_name = {X["id"]: X["name"] for X in classlist}
    # and a sid to test look up
    sid_to_test = {prenames[X]["student_id"]: X for X in prenames}
    # add any ML predictions to this list
    if use_predictions:
        for X in ml_predictions:
            if X not in sid_to_test:
                sid_to_test["student_id"] = X

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
        str_task = str(task)

        # where possible take the prenamed ID
        if str_task in prenames:
            sid = prenames[str_task]["student_id"]
            name = sid_to_name[sid]
            print(f"Task {task} prenamed to be {sid} {name} - using that")
            try:
                messenger.IDreturnIDdTask(task, sid, name)
            except PlomConflict:
                print(f"Already used: {name}")
            continue
        # otherwise try any ML predictions
        if use_predictions and str_task in ml_predictions:
            sid = ml_predictions[str_task]["student_id"]
            name = sid_to_name[sid]
            try:
                messenger.IDreturnIDdTask(task, sid, name)
                continue
            except PlomConflict:
                print(f"Already used: {name}")
        # otherwise pull a student id randomly from the classlist
        # but not one used for prenaming.
        while True:
            try:
                person = random.choice(classlist)
                if person["id"] not in sid_to_test:
                    name = person["name"] + " [randomly chosen]"
                    messenger.IDreturnIDdTask(task, person["id"], name)
                    break
            except PlomConflict:
                print(f"Already used: {person}")


def do_rando_identifying(
    server: Union[str, None], user: str, password: str, *, use_predictions: bool = False
) -> int:
    """Randomly associate papers with students: only for testing please.

    Args:
        server: which server.
        user: credientials.
        password: credientials.

    Keyword Args:
        use_predictions: download and use predictions to try to id papers. Note that
            the rando-id-er uses prenamed IDs in all cases, regardless of this setting.

    Returns:
        0 on success, non-zero on error/unexpected.
    """
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
        do_rando_identifying_backend(messenger, use_predictions=use_predictions)
    finally:
        messenger.closeUser()
        messenger.stop()
    return 0
