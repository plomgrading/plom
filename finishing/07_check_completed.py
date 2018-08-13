import os,json,csv
from testspecification import TestSpecification
from collections import defaultdict
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase
import sys
import sqlite3

sys.path.append("../imageServer")
# from id_storage import IDImage
# from mark_storage import GroupImage
#
# iddb = SqliteExtDatabase('../resources/identity.db', pragmas = {'query_only': True})
# markdb = SqliteExtDatabase('../resources/test_marks.db',pragmas = {'query_only': True})
#
# markdb.pragma('query_only', True, permanent=True)

markdb = sqlite3.connect('file:../resources/test_marks.db?mode=ro', uri=True)
curMark = markdb.cursor()

iddb = sqlite3.connect('file:../resources/identity.db?mode=ro', uri=True)
idMark = iddb.cursor()


def checkMarked(n):
    ToDo = 0
    for row in curMark.execute("SELECT * FROM groupimage WHERE status='ToDo'"):
        ToDo = ToDo + 1
    print(ToDo)
    if ToDo > 0:
        return False
    else:
        return True

def checkIDed(n):
    ToDo = 0
    for row in idMark.execute("SELECT * FROM idimage WHERE status = 'ToDo'"):
        ToDo = ToDo + 1
    print(ToDo)
    if ToDo > 0:
        return False
    else:
        return True


def readExamsGrouped():
    global examsGrouped
    if(os.path.exists("../resources/examsGrouped.json")):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)

def readExamsIDed():
    global examsIDed
    if(os.path.exists("../resources/examsIdentified.json")):
        with open('../resources/examsIdentified.json') as data_file:
            examsIDed = json.load(data_file)

def readGroupImagesMarked():
    global groupImagesMarked
    if(os.path.exists("../resources/groupImagesMarked.json")):
        with open('../resources/groupImagesMarked.json') as data_file:
            groupImagesMarked = json.load(data_file)


def checkExam(n):
    global examsIDed
    global groupImagesMarked
    print("##################\nExam {}".format(n))
    if(checkMarked(n) and checkIDed(n) ):
        print("\tComplete - build front page and reassemble.")
        return(True)
    else:
        return(False)

def writeExamsCompleted():
    fh = open("../resources/examsCompleted.json",'w')
    fh.write( json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()

def writeMarkCSV():
    head = ['StudentID','StudentName','TestNumber']
    for pg in range(1,spec.getNumberOfGroups()+1):
        head.append('PageGroup{}'.format(pg))
    head.append('Total')
    for pg in range(1,spec.getNumberOfGroups()+1):
        head.append('Version{}'.format(pg))

    with open("testMarks.csv", 'w') as csvfile:
        testWriter = csv.DictWriter(csvfile, fieldnames=head, delimiter='\t', quotechar="\"", quoting=csv.QUOTE_NONNUMERIC)
        testWriter.writeheader()
        for n in sorted(examsCompleted.keys()):
            if(examsCompleted[n]==False):
                continue
            ns = str(n)
            row=dict()
            row['StudentID'] = examsIDed[ns][1]
            row['StudentName'] = examsIDed[ns][2]
            row['TestNumber'] = n
            tot = 0
            for pg in range(1,spec.getNumberOfGroups()+1):
                p = str(pg)
                tot += groupImagesMarked[ns][p][1]
                row['PageGroup{}'.format(p)] = groupImagesMarked[ns][p][1]
                row['Version{}'.format(p)] = groupImagesMarked[ns][p][0]
            row['Total']=tot
            testWriter.writerow(row)

spec = TestSpecification()
spec.readSpec()

readExamsGrouped()
readExamsIDed()
examScores=defaultdict(list)
readGroupImagesMarked()

examsCompleted={}
for n in sorted(examsGrouped.keys()):
    examsCompleted[int(n)]=checkExam(n)

writeExamsCompleted()
writeMarkCSV()
