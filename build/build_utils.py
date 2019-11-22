# -*- coding: utf-8 -*-

"""Utilities for generating metadata for a series of tests."""

__author__ = "Andrew Rechnitzer, Colin Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import json
import sys
import shlex
import subprocess
from random import randint

sys.path.append("..")  # this allows us to import from ../resources
from resources.testspecification import TestSpecification


def buildIDPages(exams, t, idpages):
    for p in idpages:
        exams[t][str(p)] = 1  # ID pages are always version1
    return exams


def buildGroup(exams, t, pageTuple, fcr, V, v):
    if fcr == "f" or fcr == "i":  # fixed and id pages always version 1
        v = 1
    elif fcr == "r":  # pick one at random
        v = randint(1, V)
    else:  # cycle
        v += 1
        if v > V:
            v = 1
    for p in pageTuple:
        exams[t][str(p)] = v

    return v, exams


def buildDirectories():
    lst = ["examsToPrint"]
    for x in lst:
        cmd = shlex.split("mkdir -p {}".format(x))
        subprocess.call(cmd)


def buildExamPages(spec):
    """Build the metadata for a bunch of exams from a spec file

    Returns:
       exams: a dict keyed by [testnum][page]
    """
    exams = defaultdict(dict)
    npg = spec.getNumberOfGroups()
    # keep track of version of given page group in given exam so can compute cycling versions.
    ver = [0 for x in range(npg + 1)]
    for t in range(1, spec.Tests + 1):
        for k in range(1, npg + 1):  # runs from 1,2,...
            ver[k], exams = buildGroup(exams,
                t, spec.PageGroups[k], spec.FixCycleRandom[k], spec.Versions, ver[k]
            )
        exams = buildIDPages(exams, t, spec.IDGroup)
    return exams


def writeExamLog(exams):
    elFH = open("../resources/examsProduced.json", "w")
    # TODO: use of sort_keys precludes mixing int/str keys
    elFH.write(json.dumps(exams, indent=2, sort_keys=True))
    elFH.close()
