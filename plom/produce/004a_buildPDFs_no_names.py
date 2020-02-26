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
import sys

from plom import SpecParser
from plom.db.examDB import PlomDB
from .mergeAndCodePages import makePDF

examDB = PlomDB()


def buildAllPapers(spec):
    # TODO: slow serial loop, awaiting Pool ||ism
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        makePDF(
            spec["name"],
            spec["publicCode"],
            spec["numberOfPages"],
            spec["numberOfVersions"],
            t,
            pv,
        )


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
    buildAllPapers(spec)
    confirmProcessed(spec)
