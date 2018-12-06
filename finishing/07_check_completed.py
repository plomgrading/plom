from collections import defaultdict
import csv
import json
import os
import sys
import sqlite3
from testspecification import TestSpecification

# Do we need this?
# sys.path.append("../imageServer")

# Access the databases
# Open the marks database (readonly)
markdb = sqlite3.connect('file:../resources/test_marks.db?mode=ro', uri=True)
curMark = markdb.cursor()
# Open the ID database (readonly)
iddb = sqlite3.connect('file:../resources/identity.db?mode=ro', uri=True)
curID = iddb.cursor()
# Create dictionaries for the marked groups, ID'd papers and completed tests.
groupImagesMarked=defaultdict(lambda: defaultdict(list))
examsIDed = {}
completedTests=defaultdict(lambda: defaultdict(list))


def checkMarked(n):
    global groupImagesMarked
    for row in curMark.execute("SELECT * FROM groupimage WHERE number='{}'".format(n)):
        if row[7] != 'Marked':
            return False
        else:
            groupImagesMarked[n][row[4]] = [row[5], row[10]]
    return True

def checkIDed(n):
    global examsIDed
    for row in curID.execute("SELECT * FROM idimage WHERE number = '{}'".format(n)):
        if row[3] != 'Identified':
            return False
        else:
            examsIDed[n] = [row[6], row[7]] #store SID and SName
    return True


def readExamsGrouped():
    global examsGrouped
    if(os.path.exists("../resources/examsGrouped.json")):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)

def checkExam(n):
    print("Exam {}".format(n), end="")
    cm = checkMarked(n)
    ci = checkIDed(n)
    if cm:
        if ci:
            print("\tComplete - build front page and reassemble.")
            return True
        else:
            print("\tMarked but not ID'd")
            return False
    else:
        if ci:
            print("\tID'd but not marked")
            return False
        else:
            print("\tNeither ID'd nor marked")
            return False

def writeExamsCompleted():
    fh = open("../resources/examsCompleted.json",'w')
    fh.write( json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()

def writeMarkCSV():
    head = ['StudentID','StudentName','TestNumber']
    for pg in range(1,spec.getNumberOfGroups()+1):
        head.append('PageGroup{} Mark'.format(pg))
    head.append('Total')
    for pg in range(1,spec.getNumberOfGroups()+1):
        head.append('PageGroup{} Version'.format(pg))

    with open("testMarks.csv", 'w') as csvfile:
        testWriter = csv.DictWriter(csvfile, fieldnames=head, delimiter='\t', quotechar="\"", quoting=csv.QUOTE_NONNUMERIC)
        testWriter.writeheader()
        for n in sorted(examsCompleted.keys()):
            if(examsCompleted[n]==False):
                continue
            ns = str(n)
            row=dict()
            row['StudentID'] = examsIDed[ns][0]
            row['StudentName'] = examsIDed[ns][1]
            row['TestNumber'] = n
            tot = 0
            for pg in range(1,spec.getNumberOfGroups()+1):
                tot += groupImagesMarked[ns][pg][1]
                row['PageGroup{} Mark'.format(pg)] = groupImagesMarked[ns][pg][1]
                row['PageGroup{} Version'.format(pg)] = groupImagesMarked[ns][pg][0]
            row['Total']=tot
            testWriter.writerow(row)

def writeExamsIdentified():
    exid = {}
    for row in curID.execute("SELECT * FROM idimage"):
        if row[3] == 'Identified':
            exid[row[1]] = [row[2], row[6], row[7], row[4]]
    eg = open("../resources/examsIdentified.json",'w')
    eg.write(json.dumps(exid, indent=2, sort_keys=True))
    eg.close()

def writeExamsMarked():
    exid = {}
    for row in curID.execute("SELECT * FROM idimage"):
        if row[3] == 'Identified':
            exid[row[1]] = [row[2], row[6], row[7], row[4]]
    eg = open("../resources/examsIdentified.json",'w')
    eg.write(json.dumps(exid, indent=2, sort_keys=True))
    eg.close()

def writeExamsMarked():
    exmarked=defaultdict(lambda: defaultdict(list))
    for row in curMark.execute("SELECT * FROM groupimage"):
        if row[7] == 'Marked':
            exmarked[row[3]][row[4]]=[row[5], row[10], row[8]]
    eg = open("../resources/groupImagesMarked.json",'w')
    eg.write( json.dumps(exmarked, indent=2, sort_keys=True))
    eg.close()

spec = TestSpecification()
spec.readSpec()

readExamsGrouped()

examsCompleted={}
for n in sorted(examsGrouped.keys(), key=int):
    examsCompleted[int(n)]=checkExam(n)

writeExamsCompleted()
writeMarkCSV()

writeExamsIdentified()
writeExamsMarked()

markdb.close()
iddb.close()
