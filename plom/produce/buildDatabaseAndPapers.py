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


def buildDatabaseAndPapers(server=None, password=None, fakepdf=False, no_qr=False):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

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
        exit(10)
    try:
        spec = msgr.get_spec()
        print("="*80)
        print("TEMPORARILY HACKING VERSION MAP CLIENT SIDE")
        print("="*80)
        vmap = {}
        for t in range(1, spec["numberToProduce"] + 1):
            vmap[t] = {}
            for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
                gs = str(g + 1)  # now a str and 1,2,3,...
                if spec["question"][gs]["select"] == "fix":
                    vmap[t][g + 1] = 1
                elif spec["question"][gs]["select"] == "shuffle":
                    vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
                elif spec["question"][gs]["select"] == "param":
                    vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])

        try:
            status = msgr.TriggerPopulateDB(vmap)
        except PlomBenignException:
            print("Error: Server already has a populated database")
            exit(3)
        print(status)
        pvmap = msgr.getGlobalPageVersionMap()
        os.makedirs(paperdir, exist_ok=True)

        if spec["numberToName"] > 0:
            try:
                classlist = msgr.IDrequestClasslist()
            except PlomBenignException as e:
                print("Failed to download classlist: {}".format(e))
                exit(4)
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
