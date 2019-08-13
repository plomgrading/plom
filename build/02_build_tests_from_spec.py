#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

from collections import defaultdict
import json
import os
import sys
from random import randint

sys.path.append("..")  # this allows us to import from ../resources
from resources.testspecification import TestSpecification

exams = defaultdict(dict)


def buildIDPages(t, idpages):
    for p in idpages:
        exams[t][p] = 1  # ID pages are always version1


def buildGroup(t, pageTuple, fcr, V, v):
    if fcr == "f" or fcr == "i":  # fixed and id pages always version 1
        v = 1
    elif fcr == "r":  # pick one at random
        v = randint(1, V)
    else:  # cycle
        v += 1
        if v > V:
            v = 1
    for p in pageTuple:
        exams[t][p] = v

    return v


def buildExamPages(spec):
    npg = spec.getNumberOfGroups()
    # keep track of version of given page group in given exam so can compute cycling versions.
    ver = [0 for x in range(npg + 1)]
    for t in range(1, spec.Tests + 1):
        for k in range(1, npg + 1):  # runs from 1,2,...
            ver[k] = buildGroup(
                t, spec.PageGroups[k], spec.FixCycleRandom[k], spec.Versions, ver[k]
            )
        buildIDPages(t, spec.IDGroup)


def buildDirectories():
    lst = ["examsToPrint"]
    for x in lst:
        os.system("mkdir -p " + x)


def writeExamLog():
    elFH = open("../resources/examsProduced.json", "w")
    elFH.write(json.dumps(exams, indent=2, sort_keys=True))
    elFH.close()


if __name__ == '__main__':
    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    buildExamPages(spec)
    writeExamLog()
    os.system("python3 buildTestPDFs.py")
