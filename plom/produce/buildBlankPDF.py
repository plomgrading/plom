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


def _f(x):
    # TODO: unfortunate to copy spec here many times, but otherwise we get
    # AttributeError: Can't pickle local object 'buildAllPapers.<locals>.f'
    t, pv, spec = x
    makePDF(
        spec["name"],
        spec["publicCode"],
        spec["numberOfPages"],
        spec["numberOfVersions"],
        t,
        pv,
    )

def buildAllPapers(spec, dbFilename):
    examDB = PlomDB(dbFilename)
    stuff = []
    for t in range(1, spec["numberToProduce"] + 1):
        pv = examDB.getPageVersions(t)
        stuff.append((t, pv, spec))

    # Same as:
    # for x in stuff:
    #     _f(x)
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(_f, stuff), total=N))

def confirmProcessed(spec, dbFilename):
    examDB = PlomDB(dbFilename)
    for t in range(1, spec["numberToProduce"] + 1):
        fname = "papersToPrint/exam_{}.pdf".format(str(t).zfill(4))
        if os.path.isfile(fname):
            examDB.produceTest(t)
        else:
            print("Warning - where is exam pdf = {}".format(fname))
