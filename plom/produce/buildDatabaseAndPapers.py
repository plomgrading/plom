# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

import os
from getpass import getpass
import random

from plom.produce import build_all_papers, confirm_processed, identify_prenamed
from plom.produce import paperdir
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException, PlomBenignException


def build_papers(server=None, password=None, fakepdf=False, no_qr=False):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    msgr.requestAndSaveToken("manager", password)
    try:
        spec = msgr.get_spec()
        pvmap = msgr.getGlobalPageVersionMap()
        os.makedirs(paperdir, exist_ok=True)

        if spec["numberToName"] > 0:
            classlist = msgr.IDrequestClasslist()
            print(
                'Building {} pre-named papers and {} blank papers in "{}"...'.format(
                    spec["numberToName"],
                    spec["numberToProduce"] - spec["numberToName"],
                    paperdir,
                )
            )
        else:
            classlist = None
            print(
                'Building {} blank papers in "{}"...'.format(
                    spec["numberToProduce"], paperdir
                )
            )
        build_all_papers(spec, pvmap, classlist, fakepdf, no_qr=no_qr)

        print("Checking papers produced and updating databases")
        confirm_processed(spec, msgr, classlist)
        print("Identifying any pre-named papers into the database")
        identify_prenamed(spec, msgr, classlist)
    finally:
        msgr.closeUser()
        msgr.stop()


def make_random_ver_map(spec):
    """Rough client-side version map.

    args:
        spec (dict): plom spec as documented elsewhere.  TODO: maybe
            maybe better to pass only the bits we need.

    return:
        dict: a dict-of-dicts keyed by paper number (int) and then
            question number (str, b/c WTF knows).  Values are integers.
    """
    vmap = {}
    for t in range(1, Nspec["numberToProduce"] + 1):
        vmap[t] = {}
        for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
            gs = str(g + 1)  # now a str and 1,2,3,...
            if spec["question"][gs]["select"] == "fix":
                vmap[t][g + 1] = 1
            elif spec["question"][gs]["select"] == "shuffle":
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
            elif spec["question"][gs]["select"] == "param":
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
    return vmap


def build_database(server=None, password=None, vermap={}):
    """Build the database from a pre-set version map.

    args:
        vermap (dict): TODO XREF ver map tools.  If empty dict, we have
            server make its own mapping.
        server (str):
        password (str):

    return:
        str: long multiline string of all the version DB entries.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    msgr.requestAndSaveToken("manager", password)
    try:
        status = msgr.TriggerPopulateDB(vermap)
    except PlomBenignException:
        # TODO this should be a more specific exception
        raise RuntimeError("Server already has a populated database") from None

    # TODO: grab it and sanity check?
    pvmap = msgr.getGlobalPageVersionMap()
    # we want qvmap not pvmap
    #assert pvmap == vermap

    msgr.closeUser()
    msgr.stop()
    return status
