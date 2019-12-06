#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from glob import glob

from specParser import SpecParser


def buildDirectories(spec):
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["sentPages", "sentPages/problemImages"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass
    for p in range(1, spec["totalPages"] + 1):
        for v in range(1, spec["sourceVersions"] + 1):
            dir = "sentPages/page_{}/version_{}".format(str(p).zfill(2), v)
            os.makedirs(dir, exist_ok=True)


def extractTPV(name):
    # TODO - replace this with something less cludgy.
    # should be tXXXXpYYvZ.blah
    assert name[0] == "t"
    k = 1
    ts = ""
    while name[k].isnumeric():
        ts += name[k]
        k += 1

    assert name[k] == "p"
    k += 1
    ps = ""
    while name[k].isnumeric():
        ps += name[k]
        k += 1

    assert name[k] == "v"
    k += 1
    vs = ""
    while name[k].isnumeric():
        vs += name[k]
        k += 1
    return (ts, ps, vs)


def sendFiles(fileList):
    for fname in fileList:
        sname = os.path.split(fname)[1]
        ts, ps, vs = extractTPV(sname)
        # print("**********************")
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, sname))
        print(
            "If successful then move {} to sentPages subdirectory else move to problemImages".format(
                sname
            )
        )


if __name__ == "__main__":
    print(">> This is still a dummy script, but gives you the idea? <<")
    # Look for pages in decodedPages
    spec = SpecParser().spec
    buildDirectories(spec)

    for p in range(1, spec["totalPages"] + 1):
        sp = str(p).zfill(2)
        if not os.path.isdir("decodedPages/page_{}".format(sp)):
            continue
        for v in range(1, spec["sourceVersions"] + 1):
            print("Looking for page {} version {}".format(sp, v))
            if not os.path.isdir("decodedPages/page_{}/version_{}".format(sp, v)):
                continue
            fileList = glob("decodedPages/page_{}/version_{}/t*.png".format(sp, v))
            sendFiles(fileList)
