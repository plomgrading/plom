#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import csv
import json
import os
import sys
import shlex
import subprocess
from random import randint

sys.path.append("..")  # this allows us to import from ../resources
from resources.testspecification import TestSpecification

exams = defaultdict(dict)
students = {}


def readClassList():
    # read in the classlist
    with open("../resources/classlist.csv", newline="") as csvfile:
        red = csv.reader(csvfile, delimiter=",")
        next(red, None)
        k = 0
        for row in red:
            k += 1
            students[k] = [row[0], row[1]]


def nameExam(t):
    if t in students:
        exams[t]["id"] = students[t][0]
        exams[t]["name"] = students[t][1]


def buildIDPages(t, idpages):
    for p in idpages:
        exams[t][str(p)] = 1  # ID pages are always version1


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
        exams[t][str(p)] = v

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
        nameExam(t)


def buildDirectories():
    lst = ["examsToPrint"]
    for x in lst:
        cmd = shlex.split("mkdir -p {}".format(x))
        subprocess.call(cmd)


def writeExamLog():
    print(exams)
    elFH = open("../resources/examsProduced.json", "w")
    elFH.write(json.dumps(exams, indent=2, sort_keys=True))
    elFH.close()


if __name__ == "__main__":
    spec = TestSpecification()
    spec.readSpec()
    readClassList()
    buildDirectories()
    buildExamPages(spec)
    writeExamLog()
    cmd = shlex.split("python3 buildTestPDFs.py")
    subprocess.call(cmd)
