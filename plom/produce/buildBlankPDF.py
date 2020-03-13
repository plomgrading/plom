#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from multiprocessing import Pool
from tqdm import tqdm

from plom.db.examDB import PlomDB
from .mergeAndCodePages import makePDF


def _makePDF(x):
    makePDF(*x)


def buildAllPapers(spec, dbFilename):
    examDB = PlomDB(dbFilename)
    makePDFargs = []
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        makePDFargs.append(
            (
                spec["name"],
                spec["publicCode"],
                spec["numberOfPages"],
                spec["numberOfVersions"],
                t,
                pv,
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
            print("Warning - where is exam pdf = {}".format(fname))
