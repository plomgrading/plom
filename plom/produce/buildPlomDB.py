#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
from plom.db import PlomDB


def buildExamDatabase(spec, dbFname):
    """Build metadata for exams from spec and insert into the database.

    Arguments:
        spec {dict} -- The spec file for the database that is being setup.
                          Example below:
                          {
                            'name': 'plomdemo',
                            'longName': 'Midterm Demo using Plom',
                            'numberOfVersions': 2,
                            'numberOfPages': 6,
                            'numberToProduce': 20,
                            'numberToName': 10,
                            'numberOfQuestions': 3,
                            'privateSeed': '1001378822317872',
                            'publicCode': '270385',
                            'idPages': {'pages': [1]},
                            'doNotMark': {'pages': [2]},
                            'question': {
                                '1': {'pages': [3], 'mark': 5, 'select': 'shuffle'},
                                '2': {'pages': [4], 'mark': 10, 'select': 'fix'},
                                '3': {'pages': [5, 6], 'mark': 10, 'select': 'shuffle'} }
                            }
                          }
        dbFname {str} -- The name of the database we are creating.
    """

    random.seed(spec["privateSeed"])
    examDB = PlomDB(dbFname)

    errFlag = False
    for q in range(spec["numberOfQuestions"]):
        for v in range(spec["numberOfVersions"]):
            if examDB.createAnnotationBundle(q + 1, v + 1):
                print("Created image bundle for q.v={}.{}".format(q + 1, v + 1))
            else:
                print(
                    "Error - problem creating image bundle for q.v={}.{}".format(
                        q + 1, v + 1
                    )
                )
                errFlag = True

    # Note: need to produce these in a particular order for random seed to be
    # reproducibile: so this really must be a loop, not a Pool.
    for t in range(1, spec["numberToProduce"] + 1):
        if examDB.createTest(t):
            print("DB entry for test {:04}:".format(t), end="")
        else:
            print("Error - problem creating test {}".format(t))
            errFlag = True

        if examDB.createIDGroup(t, spec["idPages"]["pages"]):
            print(" ID", end="")
        else:
            print("Error - problem creating idgroup for test {}".format(t))
            errFlag = True

        if examDB.createDNMGroup(t, spec["doNotMark"]["pages"]):
            print(" DNM", end="")
        else:
            print("Error - problem creating DoNotMark-group for test {}".format(t))
            errFlag = True

        for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
            gs = str(g + 1)  # now a str and 1,2,3,...
            if (
                spec["question"][gs]["select"] == "fix"
            ):  # there is only one version so all are version 1
                v = 1
                vstr = "f{}".format(v)
            elif (
                spec["question"][gs]["select"] == "shuffle"
            ):  # version selected randomly in [1, 2, ..., #versions]
                v = random.randint(1, spec["numberOfVersions"])
                vstr = "v{}".format(v)
            else:
                print(
                    'ERROR - problem with spec: expected "fix" or "shuffle" but got "{}".'.format(
                        spec["question"][gs]["select"]
                    )
                )
                exit(1)
            if examDB.createQGroup(t, int(gs), v, spec["question"][gs]["pages"]):
                print(" Q{}{}".format(gs, vstr), end="")
            else:
                print("Error - problem creating Question {} for test {}".format(gs, t))
                errFlag = True
        print("")
    if errFlag:
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
        print(
            "There were errors during database creation. Remove the database and try again."
        )
        print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<")
