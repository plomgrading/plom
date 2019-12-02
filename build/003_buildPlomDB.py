#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import random
import toml
import json

from specParser import SpecParser
from examDB import *

examDB = PlomDB()


def buildDirectories():
    os.makedirs("examsToPrint", exist_ok=True)


def buildExamDatabase(spec):
    """Build the metadata for a bunch of exams from a spec file

    Returns:
       exams: a dict keyed by [testnum][page]
    """
    exams = defaultdict(dict)
    for t in range(1, spec["numberToProduce"] + 1):
        examDB.addTest(t)
        examDB.addIDGroup(t, spec["idPages"]["pages"])
        examDB.addDNMGroup(t, spec["doNotMark"]["pages"])

    #     pv = dict()
    #     # build the ID-pages - always version 1
    #     for p in spec["idPages"]["pages"]:
    #         pv[str(p)] = 1
    #     # build the DoNotMark-pages - always version 1
    #     for p in spec["doNotMark"]["pages"]:
    #         pv[str(p)] = 1
    #     # now build the groups
    #     for g in range(spec["numberOfGroups"]):  # runs from 0,1,2,...
    #         gs = str(g + 1)  # now 1,2,3,...
    #         # if selection = fixed, then all are version 1
    #         if spec[gs]["select"] == "fixed":
    #             for p in spec[gs]["pages"]:
    #                 pv[str(p)] = 1
    #         # if selection = shuffle, then the group is selected randomly
    #         elif spec[gs]["select"] == "shuffle":
    #             v = random.randint(
    #                 1, spec["sourceVersions"]
    #             )  # version selected randomly [1,2,..#versions]
    #             for p in spec[gs]["pages"]:
    #                 pv[str(p)] = v
    #         else:
    #             print("ERROR - problem with specification. Please check it carefully.")
    #             exit(1)
    #     exams[t] = pv
    # return exams


if __name__ == "__main__":
    # buildDirectories()
    spec = SpecParser().spec
    # set the random number seed from the spec.
    random.seed(spec["privateSeed"])
    buildExamDatabase(spec)

    # build the exam pages (ie - select which pages from which version)
    # buildExamDatabase(spec)
