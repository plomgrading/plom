#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import sys

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification
from resources.misc_utils import format_int_list_with_runs


def readExamsScanned():
    """Read the test/page we have scanned in 03/04 scripts"""
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open("../resources/examsScanned.json") as data_file:
            examsScanned = json.load(data_file)


def checkTestComplete(t):
    """Check the given test to see if all pages are present
    print appropriate message and return true if complete,
    false otherwise.
    Note this only checks tests for which we have scanned
    at least one page. It will not report any un-used test.
    """
    # list for missing pages
    missing = []
    for p in range(1, spec.Length + 1):
        # if page not in scanned list then add it to missing.
        if str(p) not in examsScanned[t]:
            missing.append(p)
    # If any pages in the missing list print warning
    if missing:
        print(">> Test {} is missings pages".format(t), missing)
        return False
    else:
        print("Test {} is complete".format(t))
        return True


if __name__ == '__main__':
    spec = TestSpecification()
    spec.readSpec()
    readExamsScanned()

    # lists for complete / incomplete tests
    completeTests = []
    incompleteTests = []
    # Check tests in numerical order
    for t in sorted(examsScanned.keys(), key=int):
        if checkTestComplete(t):
            completeTests.append(t)
        else:
            incompleteTests.append(t)

    print("###################### ")
    s = format_int_list_with_runs(completeTests) if completeTests else u"None 🙁"
    print("Complete test papers are: " + s)
    print("###################### ")
    s = format_int_list_with_runs(incompleteTests) if incompleteTests else u"None 😀"
    print("Incomplete test papers are: " + s)
    print("###################### ")
