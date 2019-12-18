#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import os
import random
import shlex
import subprocess

# this allows us to import from ../resources
sys.path.append("..")
from resources.specParser import SpecParser
from resources.examDB import *

examDB = PlomDB()


def readClassList():
    students = {}
    # read in the classlist
    with open("../resources/classlist.csv", newline="") as csvfile:
        red = csv.reader(csvfile, delimiter=",")
        next(red, None)
        k = 0
        for row in red:
            k += 1
            students[k] = [row[0], row[1]]
    return students


def buildCommandList(spec, students):
    cmdList = []
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        # have to add name/id to pv
        if t <= spec["numberToName"]:
            pv["id"] = students[t][0]
            pv["name"] = students[t][1]
        cmdList.append(
            'python3 mergeAndCodePages.py {} {} {} {} {} "{}"\n'.format(
                spec["name"],
                spec["publicCode"],
                spec["numberOfPages"],
                spec["numberOfVersions"],
                t,
                pv,
            )
        )
    return cmdList


def runCommandList(cmdList):
    with open("./commandlist.txt", "w") as fh:
        for c in cmdList:
            fh.write(c)

    cmd = shlex.split("parallel --bar -a commandlist.txt")
    subprocess.run(cmd, check=True)


def confirmProcessedAndNamed(spec, students):
    for t in range(1, spec["numberToProduce"] + 1):
        fname = "examsToPrint/exam_{}.pdf".format(str(t).zfill(4))
        if os.path.isfile(fname):
            examDB.produceTest(t)
            if t <= spec["numberToName"]:
                examDB.identifyTest(t, students[t][0], students[t][1])
        else:
            print("Warning - where is exam pdf = {}".format(fname))


if __name__ == "__main__":
    # read the spec
    spec = SpecParser().spec
    students = readClassList()
    cmdList = buildCommandList(spec, students)
    runCommandList(cmdList)
    confirmProcessedAndNamed(spec, students)
