# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import random
from plom.db import PlomDB


def buildExamDatabaseFromSpec(spec, db):
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
        db (database): the database to populate.

    Returns:
        bool: True if succuess.
        str: a status string, one line per test, ending with an error if failure.

    Raises:
        ValueError: if database already populated.
    """
    # fire up logging
    import logging

    log = logging.getLogger("DB")

    if db.areAnyPapersProduced():
        raise ValueError("Database already populated")

    random.seed(spec["privateSeed"])

    ok = True
    status = ""
    # build bundles for annotation images
    # for q in range(1, 1 + spec["numberOfQuestions"]):
    # for v in range(1, 1 + spec["numberOfVersions"]):
    # pass
    # if not db.createAnnotationBundle(q, v):
    #     ok = False
    #     status += "Error making bundle for q.v={}.{}".format(q, v)
    # build bundle for replacement pages (for page-not-submitted images)

    if not db.createReplacementBundle():
        ok = False
        status += "Error making bundle for replacement pages"

    # Note: need to produce these in a particular order for random seed to be
    # reproducibile: so this really must be a loop, not a Pool.
    for t in range(1, spec["numberToProduce"] + 1):
        log.info(
            "Creating DB entry for test {} of {}.".format(t, spec["numberToProduce"])
        )
        if db.createTest(t):
            status += "DB entry for test {:04}:".format(t)
        else:
            status += " Error creating"
            ok = False

        if db.createIDGroup(t, spec["idPages"]["pages"]):
            status += " ID"
        else:
            status += " Error creating idgroup"
            ok = False

        if db.createDNMGroup(t, spec["doNotMark"]["pages"]):
            status += " DNM"
        else:
            status += "Error creating DoNotMark-group"
            ok = False

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
                # TODO: or RuntimeError?
                raise ValueError(
                    'problem with spec: expected "fix" or "shuffle" but got "{}".'.format(
                        spec["question"][gs]["select"]
                    )
                )
            if db.createQGroup(t, int(gs), v, spec["question"][gs]["pages"]):
                status += " Q{}{}".format(gs, vstr)
            else:
                status += "Error creating Question {} ver {}".format(gs, vstr)
                ok = False
        status += "\n"

    print("ok, status = ", ok, status)
    return ok, status
