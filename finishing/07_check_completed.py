#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin B. Macdonald", "Elvis Cai"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import csv
import json
import os
import sqlite3
import sys

from utils import format_int_list_with_runs
# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification

# Do we need this?
# sys.path.append("../imageServer")


def checkMarked(n):
    """Look at the mark datbase and extract which groups of test n are
    marked and record in a dictionary
    """
    global groupImagesMarked
    global pgStatus
    # Extract all marked images from test n from the mark database
    # A row of the table in the Mark DB is
    # 0=index, 1=TGV, 2=originalFile, 3=testnumber, 4=pageGroup
    # 5=version, 6=annotatedFile, 7=plomFile, 8=commentFile,
    # 9=status, 10=user, 11=time, 12=mark, 13=timeSpentMarking,
    # 14=tags
    unmarked = True
    for row in curMark.execute("SELECT * FROM groupimage WHERE number='{}'".format(n)):
        if row[9] != "Marked":
            unmarked = False
        else:
            # Save the version and mark in the dictionary.
            groupImagesMarked[n][row[4]] = [row[5], row[12]]
            pgStatus[row[4]] += 1
    return unmarked


def displayMarked(n):
    s = "["
    for pg in range(1, spec.getNumberOfGroups() + 1):
        if len(groupImagesMarked[n][pg]) > 0:
            s += "x"
        else:
            s += "."
    s += "]"
    return s


def printPGStatus(totalPapers):
    global pgStatus
    for pg in range(1, spec.getNumberOfGroups() + 1):
        print("Group {}: {} of {} completed".format(pg, pgStatus[pg], totalPapers))


def checkIDed(n):
    """Look at the ID database and see if test n has been ID'd.
    Store the result in examsIDed dictionary.
    """
    global examsIDed
    # Extract test number n and look if it has been ID'd
    # A row of the table in the ID DB is
    # 0=index, 1=TestNumber, 2=tgv, 3=status, 4=user
    # 5=time, 6=StudentID, 7=StudentName.
    for row in curID.execute("SELECT * FROM idimage WHERE number = '{}'".format(n)):
        if row[3] != "Identified":
            return False
        else:
            # store StudentID and StudentName
            examsIDed[n] = [row[6], row[7]]
    return True


def readExamsGrouped():
    """Read the list of exams that were grouped after scanning.
    Store in examsGrouped.
    """
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open("../resources/examsGrouped.json") as data_file:
            examsGrouped = json.load(data_file)


def checkExam(n):
    """Look at test number n and see if ID'd and marked. Report to user.
    Return true if both marked and ID'd and false otherwise
    """
    print("Exam {}".format(n), end="")
    cm = checkMarked(n)
    ci = checkIDed(n)
    if cm:
        if ci:
            completeTests.append(n)
            print("\tComplete - build front page and reassemble.")
            return True
        else:
            print("\tMarked but not ID'd")
            return False
    else:
        unmarkedTests.append(n)
        if ci:
            print("\tID'd but not marked", end="")
        else:
            print("\tNeither ID'd nor marked", end="")
        # now print a diagnostic of what is actually marked/not
        print("\t{}".format(displayMarked(n)))
        return False


def writeExamsCompleted():
    """Dump a json file of all completed (ie marked+ID'd) exams.
    Each entry is just true/false.
    """
    fh = open("../resources/examsCompleted.json", "w")
    fh.write(json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()


def writeMarkCSV():
    """Write the test marks to a CSV.
    Columns are StudentID, StudentName, TestNumber, then the mark for each
    pageGroup, the total mark, and finally the version for each pagegroup.
    """
    # Construct the header
    head = ["StudentID", "StudentName", "TestNumber"]
    for pg in range(1, spec.getNumberOfGroups() + 1):
        head.append("PageGroup{} Mark".format(pg))
    head.append("Total")
    for pg in range(1, spec.getNumberOfGroups() + 1):
        head.append("PageGroup{} Version".format(pg))
    # Write a tab-delimited csv (should that be a tsv?)
    with open("testMarks.csv", "w") as csvfile:
        testWriter = csv.DictWriter(
            csvfile,
            fieldnames=head,
            delimiter="\t",
            quotechar='"',
            quoting=csv.QUOTE_NONNUMERIC,
        )
        testWriter.writeheader()
        # Look through all the completed exams and write only completed ones.
        for n in sorted(examsCompleted.keys()):
            if not examsCompleted[n]:
                # if incomplete then skip it.
                # Perhaps we should have the option of writing the incomplete ones?
                continue
            # Construct the row for output.
            ns = str(n)
            row = dict()
            row["StudentID"] = examsIDed[ns][0]
            row["StudentName"] = examsIDed[ns][1]
            row["TestNumber"] = n
            tot = 0
            for pg in range(1, spec.getNumberOfGroups() + 1):
                tot += groupImagesMarked[ns][pg][1]
                row["PageGroup{} Mark".format(pg)] = groupImagesMarked[ns][pg][1]
                row["PageGroup{} Version".format(pg)] = groupImagesMarked[ns][pg][0]
            row["Total"] = tot
            # write the row to the csv.
            testWriter.writerow(row)


def writeExamsIdentified():
    """Write to resources/examsIdentified.json file of the ID'd exams.
    Each row indexed by testnumber and contains
    TGV, StudentID, StudentName, and user who ID'd it
    """
    exid = {}
    # A row of the table in the ID DB is
    # 0=index, 1=TestNumber, 2=tgv, 3=status, 4=user
    # 5=time, 6=StudentID, 7=StudentName.
    for row in curID.execute("SELECT * FROM idimage"):
        if row[3] == "Identified":
            exid[row[1]] = [row[2], row[6], row[7], row[4]]
    # dump to json in resources directory.
    eg = open("../resources/examsIdentified.json", "w")
    eg.write(json.dumps(exid, indent=2, sort_keys=True))
    eg.close()


def writeExamsMarked():
    """Write to resources/groupImagesMarked.json file of the marked groups.
    Each entry is indexed  by testnumber and pageGroup.
    It contains, version, mark and user who marked it.
    """
    exmarked = defaultdict(lambda: defaultdict(list))
    # Extract all marked images from test n from the mark database
    # A row of the table in the Mark DB is
    # 0=index, 1=TGV, 2=originalFile, 3=testnumber, 4=pageGroup
    # 5=version, 6=annotatedFile, 7=plomFile, 8=commentFile,
    # 9=status, 10=user, 11=time, 12=mark, 13=timeSpentMarking,
    # 14=tags
    for row in curMark.execute("SELECT * FROM groupimage"):
        if row[9] == "Marked":
            exmarked[row[3]][row[4]] = [row[5], row[12], row[10]]
    # dump to json in resources directory.
    eg = open("../resources/groupImagesMarked.json", "w")
    eg.write(json.dumps(exmarked, indent=2, sort_keys=True))
    eg.close()


if __name__ == '__main__':
    # load the test specification
    spec = TestSpecification()
    spec.readSpec()
    # read the list of exams grouped after scanning.
    readExamsGrouped()
    # Access the databases
    # Open the marks database (readonly)
    markdb = sqlite3.connect("file:../resources/test_marks.db?mode=ro", uri=True)
    curMark = markdb.cursor()
    # Open the ID database (readonly)
    iddb = sqlite3.connect("file:../resources/identity.db?mode=ro", uri=True)
    curID = iddb.cursor()
    # Create dictionaries for the marked groups, ID'd papers and completed tests.
    groupImagesMarked = defaultdict(lambda: defaultdict(list))
    examsIDed = {}
    examsCompleted = {}
    # lists for complete / incomplete tests
    completeTests = []
    unmarkedTests = []
    pgStatus = defaultdict(int)
    # check each of the grouped exams.
    for n in sorted(examsGrouped.keys(), key=int):
        examsCompleted[int(n)] = checkExam(n)
    # print summary
    print("###################### ")
    s = format_int_list_with_runs(completeTests) if completeTests else u"None 🙁"
    print("Complete papers are: " + s)
    print("###################### ")
    s = format_int_list_with_runs(unmarkedTests) if unmarkedTests else u"None 😀"
    print("Not completely marked papers are: " + s)
    print("###################### ")
    print("Pagegroup status: ")
    printPGStatus(len(examsGrouped))
    print("###################### ")

    # write the json of exams completed, the CSV of marks.
    writeExamsCompleted()
    writeMarkCSV()
    # write json of exams ID'd and groups marked.
    writeExamsIdentified()
    writeExamsMarked()
    # close up the databases.
    markdb.close()
    iddb.close()
    if unmarkedTests:
        exit(1)
    exit(0)
