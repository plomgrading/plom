#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import random
import shlex
import subprocess

from examDB import *
from specParser import SpecParser

examDB = PlomDB()


def buildCommandList(spec):
    cmdList = []
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        cmdList.append(
            'python3 mergeAndCodePages.py {} {} {} {} {} "{}"\n'.format(
                spec["name"],
                spec["publicCode"],
                spec["totalPages"],
                spec["sourceVersions"],
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


def confirmProcessed(spec):
    for t in range(1, spec["numberToProduce"] + 1):
        fname = "examsToPrint/exam_{}.pdf".format(str(t).zfill(4))
        if os.path.isfile(fname):
            examDB.produceTest(t)
        else:
            print("Warning - where is exam pdf = {}".format(fname))


if __name__ == "__main__":
    # read the spec
    spec = SpecParser().spec
    cmdList = buildCommandList(spec)
    runCommandList(cmdList)
    confirmProcessed(spec)
