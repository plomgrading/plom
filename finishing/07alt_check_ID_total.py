__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from collections import defaultdict
import csv
import json
import os
import sqlite3
import sys

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


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


def checkTotaled(n):
    """Look at the Total database and see if test n has been totaled.
    Store the result in examsTotaled dictionary.
    """
    global examsTotaled
    # Extract test number n and look if it has been ID'd
    # A row of the table in the ID DB is
    # 0=index, 1=TestNumber, 2=tgv, 3=status, 4=user
    # 5=time, 6=StudentID, 7=StudentName.
    for row in curTotal.execute(
        "SELECT * FROM totalimage WHERE number = '{}'".format(n)
    ):
        if row[3] != "Totaled":
            return False
        else:
            # store StudentID and StudentName
            examsTotaled[n] = row[6]
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
    ci = checkIDed(n)
    ct = checkTotaled(n)
    if ci:
        if ct:
            print("\tComplete - totaled and ID'd.")
            return True
        else:
            print("\tID'd but not totaled")
            return False
    else:
        if ct:
            print("\tTotaled but not ID'd")
            return False
        else:
            print("\tNeither ID'd nor Totaled")
            return False


def writeIDTotalCSV():
    """Write the ID and Total to a CSV.
    Columns are StudentID, StudentName, TestNumber, then the total.
    """
    # Construct the header
    head = ["StudentID", "StudentName", "TestNumber", "Total"]
    # Write a tab-delimited csv (should that be a tsv?)
    with open("id_and_total.csv", "w") as csvfile:
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
            row["Total"] = examsTotaled[ns]
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


def writeExamsTotaled():
    """Write to resources/examsTotaled.json file of the totaled exams.
    Each row indexed by testnumber and contains
    TGV, Total, and user who totaled it
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


# load the test specification
spec = TestSpecification()
spec.readSpec()
# read the list of exams grouped after scanning.
readExamsGrouped()
# Access the databases
# Open the marks database (readonly)
totaldb = sqlite3.connect("file:../resources/totals.db?mode=ro", uri=True)
curTotal = totaldb.cursor()
# Open the ID database (readonly)
iddb = sqlite3.connect("file:../resources/identity.db?mode=ro", uri=True)
curID = iddb.cursor()
# Create dictionaries for the marked groups, ID'd papers and completed tests.
examsIDed = {}
examsTotaled = {}
examsCompleted = {}
# check each of the grouped exams.
for n in sorted(examsGrouped.keys(), key=int):
    examsCompleted[int(n)] = checkExam(n)
# write CSV of test, id and mark
writeIDTotalCSV()
# write json of exams ID'd and groups marked.
writeExamsIdentified()
writeExamsTotaled()
# close up the databases.
totaldb.close()
iddb.close()
