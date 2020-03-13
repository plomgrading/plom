#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import os
from multiprocessing import Pool
from tqdm import tqdm

from plom.db.examDB import PlomDB
from .mergeAndCodePages import makePDF


# TODO: maybe functions in this module should expect classlist as an input?
# TODO: its a bit strange to be reading the class list here.
#
# TODO: even worse, the row indices are mapped to test numbers in a way that
# TODO: may not be obvious (the `confirmedNamed` fcn).  Needs some re-org.
def readClassList():
    students = {}
    # read in the classlist
    with open(os.path.join("specAndDatabase", "classlist.csv"), newline="") as csvfile:
        red = csv.reader(csvfile, delimiter=",")
        next(red, None)
        k = 0
        for row in red:
            k += 1
            students[k] = [row[0], row[1]]
    return students


def _makePDF(x):
    makePDF(*x)


def buildAllPapers(spec, dbFilename, named=False):
    if named:
        students = readClassList()
    examDB = PlomDB(dbFilename)
    makePDFargs = []
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        if named and t <= spec["numberToName"]:
            d = {"id": students[t][0], "name": students[t][1]}
        else:
            d = None
        makePDFargs.append(
            (
                spec["name"],
                spec["publicCode"],
                spec["numberOfPages"],
                spec["numberOfVersions"],
                t,
                pv,
                d,
            )
        )

    # Same as:
    # for x in makePDFargs:
    #     makePDF(*x)
    N = len(makePDFargs)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(_makePDF, makePDFargs), total=N))


def confirmProcessed(spec, dbFilename):
    examDB = PlomDB(dbFilename)
    for t in range(1, spec["numberToProduce"] + 1):
        fname = "papersToPrint/exam_{}.pdf".format(str(t).zfill(4))
        if os.path.isfile(fname):
            examDB.produceTest(t)
        else:
            raise RuntimeError('Cannot find pdf for paper "{}"'.format(fname))


def confirmNamed(spec, dbFilename):
    students = readClassList()
    examDB = PlomDB(dbFilename)
    for t in range(1, spec["numberToProduce"] + 1):
        if t <= spec["numberToName"]:
            fname = "papersToPrint/exam_{}.pdf".format(str(t).zfill(4))
            if os.path.isfile(fname):
                examDB.identifyTest(t, students[t][0], students[t][1])
            else:
                raise RuntimeError('Cannot find pdf for paper "{}"'.format(fname))
