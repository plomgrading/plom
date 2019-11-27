#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
from warnings import warn

from build_utils import (
    buildDirectories,
    buildExamPages,
    writeExamLog,
    TestSpecification,
    buildTestPDFs,
)


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


def prefillNamesOnExams(spec, exams, students):
    for t in range(1, spec.Tests + 1):
        if t in students:
            exams[t]["id"] = students[t][0]
            exams[t]["name"] = students[t][1]
    return exams


if __name__ == "__main__":
    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    exams = buildExamPages(spec)
    students = readClassList()

    print(
        "Creating {} exams: {} will have student name/number pre-written, "
        "{} will be spare blanks.".format(
            spec.Tests, len(students), spec.Tests - len(students)
        )
    )
    warnFlag = False
    # check number of tests and issue warnings
    if len(students) > spec.Tests:
        warn(
            "Too few tests for the length of your class-list. Consider making more tests."
        )
        warnFlag = True
    if (
        spec.Tests - len(students) < 0.05 * len(students)
        or spec.Tests - len(students) < 3
    ):
        warn(
            "We think you might not have produced enough spare blanks tests. Please double-check."
        )
        warnFlag = True
    # now do the actual build
    exams = prefillNamesOnExams(spec, exams, students)
    writeExamLog(exams)
    buildTestPDFs(spec, exams)
    # if a warning was issued - remind the user to check the output
    if warnFlag:
        warn(
            "A warning was issued above, please double-check the number of tests and length of classlist."
        )
