# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import os

import getpass  # local?

from plom import SpecParser
from plom import specdir
from plom.produce import build_all_papers, confirm_processed, confirm_named
from plom.produce import paperdir
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import *

dbfile = os.path.join(specdir, "plom.db")

# todo: support both direct DB file or via server?
# TODO or remove?
def _buildDatabase(spec):
    from plom.db import buildExamDatabaseFromSpec, PlomDB

    if os.path.isfile(dbfile):
        print("Database already exists - aborting.")
        exit(1)

    print("Populating Plom exam database")
    DB = PlomDB(dbfile)
    buildExamDatabaseFromSpec(spec, DB)
    print("Database populated successfully")


def buildBlankPapers(spec):
    print("Building blank papers")
    build_all_papers(spec, dbfile)
    print("Checking papers produced and updating databases")
    confirm_processed(spec, dbfile)


def buildNamedPapers(spec):
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

    build_all_papers(spec, dbfile, named=True)
    print("Checking papers produced and updating databases")
    confirm_processed(spec, dbfile)
    confirm_named(spec, dbfile)


def buildDatabaseAndPapers(server=None, password=None, blank=False, localonly=False):
    print("Reading specification")
    if not os.path.isfile(os.path.join(specdir, "verifiedSpec.toml")):
        print('Cannot find verified specFile - have you run "plom-build parse" yet?')
        exit(1)
    spec = SpecParser().spec

    if blank == "true" and spec["numberToName"] > 0:
        print(
            ">>> WARNING <<< "
            "Your spec says to produce {} named-papers, but you have run with the '--blank' option. Building unnamed papers.".format(
                spec["numberToName"]
            )
        )

    if localonly:
        _buildDatabase(spec)
    else:
        doTheThing(server, password)
        # TODO: need pagever mapping or many api calls

    os.makedirs(paperdir, exist_ok=True)
    if blank:
        buildBlankPapers(spec)
    else:
        buildNamedPapers(spec)


#def doTheThing2(server=None, password=None, local=False):
#    if not local:
#        doTheThing(server, password)


def doTheThing(server=None, password=None):
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

    # get started
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

    #spec = msgr.getInfoGeneral()
    msgr.TriggerPopulateDB(force=False)

    msgr.closeUser()
    msgr.stop()
