#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
from plom.db.examDB import *


def buildExamDatabase(spec, dbFname):
    """Build the metadata for a bunch of exams from a spec file
    and inserts all into the database.

    """

    random.seed(spec["privateSeed"])
    examDB = PlomDB(dbFname)

    errFlag = False
    for t in range(1, spec["numberToProduce"] + 1):
        if examDB.createTest(t):
            print("Test {} created".format(t))
        else:
            print("Error - problem creating test {}".format(t))
            errFlag = True

        if examDB.createIDGroup(t, spec["idPages"]["pages"]):
            print("\tID-group created")
        else:
            print("Error - problem creating idgroup for test {}".format(t))
            errFlag = True

        if examDB.createDNMGroup(t, spec["doNotMark"]["pages"]):
            print("\tDoNotMark-group created")
        else:
            print("Error - problem creating DoNotMark-group for test {}".format(t))
            errFlag = True

        for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
            gs = str(g + 1)  # now 1,2,3,...
            if spec["question"][gs]["select"] == "fixed":  # all are version 1
                v = 1
            elif (
                spec["question"][gs]["select"] == "shuffle"
            ):  # version selected randomly
                v = random.randint(
                    1, spec["numberOfVersions"]
                )  # version selected randomly [1,2,..#versions]
            else:
                print(
                    "ERROR - problem with specification - this should not happen!! Please check it carefully."
                )
                exit(1)
            if examDB.createQGroup(t, int(gs), v, spec["question"][gs]["pages"]):
                print("\tQuestion {} created".format(gs))
            else:
                print("Error - problem creating Question {} for test {}".format(gs, t))
                errFlag = True
    if errFlag:
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
        print(
            "There were errors during database creation. Remove the database and try again."
        )
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
    else:
        print("Database created successfully")
