import os,json,csv
from testspecification import TestSpecification
from collections import defaultdict
from peewee import *
import sys

sys.path.append("../imageServer")
from id_storage import IDImage
from mark_storage import GroupImage

iddb = SqliteDatabase('../resources/identity.db')
markdb = SqliteDatabase('../resources/test_marks.db')

def checkMark(n):
        print("using my checkMark")
        CorrPerson = GroupImage.get(GroupImage.id == n)
        if CorrPerson.status == 'ToDo':
            print("not all pages are marked")
            return(False)
        else:
            print("all pages are marked")
            return(True)

def checkID(n):
        print("using my checkID")
        CorrPerson = IDImage.get(IDImage.id == n)
        if CorrPerson.status == 'ToDo':
            print("not all pages are IDed")
            return(False)
        else:
            print("all pages are Ided")
            return(True)


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

# def checkMarked(n):
#     if(n not in groupImagesMarked):
#         print("\tTotally unmarked")
#         return(False)
#     flag=True
#     for pg in range(1,spec.getNumberOfGroups()+1):
#         pgs = str(pg)
#         if( pgs not in groupImagesMarked[n] ):
#             flag=False
#
#     if(flag==False):
#         print("\tPartially marked")
#     return(flag)
#
# def checkIDed(n):
#     print("\tID image {}".format(examsGrouped[n][0]), end='')
#     if(n not in examsIDed):
#         print("\tNo ID")
#         return(False)
#     else:
#         print("\tID = ", examsIDed[n][1:3])
#         return(True)

def checkExam(n):
    global examsIDed
    global groupImagesMarked
    print("##################\nExam {}".format(n))
    if( checkMark(n) and checkID(n) ):
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
