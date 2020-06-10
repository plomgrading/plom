# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import os
import sys

import getpass  # local?

from plom import SpecParser
from plom import specdir
from plom.produce import build_all_papers, confirm_processed, confirm_named
from plom.produce import paperdir
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import *

# todo: support both direct DB file or via server?
# TODO or remove?
def _buildDatabase(spec):
    from plom.db import buildExamDatabaseFromSpec, PlomDB
    dbfile = os.path.join(specdir, "plom.db")

    if os.path.isfile(dbfile):
        print("Database already exists - aborting.")
        sys.exit(1)

    print("Populating Plom exam database")
    DB = PlomDB(dbfile)
    r, st = buildExamDatabaseFromSpec(spec, DB)
    print(st)
    if not r:
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
        print(
            "There were errors during database creation. Remove the database and try again."
        )
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
        sys.exit(2)
    print("Database populated successfully")
    print("Producing local page->version map")
    vers = {}
    for paper_idx in range(1, spec["numberToProduce"] + 1):
        ver = DB.getPageVersions(paper_idx)
        if not ver:
            raise RuntimeError("we expected each paper to exist!")
        vers[paper_idx] = ver
    return vers


def buildNamedPapers(spec, pvmap):
    if spec["numberToName"] > 0:
        print(
            'Building {} pre-named papers and {} blank papers in "{}"...'.format(
                spec["numberToName"],
                spec["numberToProduce"] - spec["numberToName"],
                paperdir,
            )
        )
    else:
        print(
            'Building {} blank papers in "{}"...'.format(
                spec["numberToProduce"], paperdir
            )
        )

    build_all_papers(spec, pvmap, named=True)


def buildDatabaseAndPapers(server=None, password=None, localonly=False):
    print("Reading specification")
    if not os.path.isfile(os.path.join(specdir, "verifiedSpec.toml")):
        print('Cannot find verified specFile - have you run "plom-build parse" yet?')
        exit(1)
    spec = SpecParser().spec

    if localonly:
        pvmap = _buildDatabase(spec)
        os.makedirs(paperdir, exist_ok=True)
        buildNamedPapers(spec, pvmap)
        print("Papers build locally, but they are not connected to the server.")
        print("Be careful!")
        return

    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass('Please enter the "manager" password: ')
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    try:
        msgr.requestAndSaveToken("manager", pwd)
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
        #spec = msgr.getInfoGeneral()
        r, status = msgr.TriggerPopulateDB(force=False)
        print(status)
        pvmap = msgr.getGlobalPageVersionMap()
        os.makedirs(paperdir, exist_ok=True)
        buildNamedPapers(spec, pvmap)

        print("Checking papers produced and updating databases")
        confirm_processed(spec, msgr)
    finally:
        msgr.closeUser()
        msgr.stop()
    dbfile = os.path.join(specdir, "plom.db")
    confirm_named(spec, dbfile)
