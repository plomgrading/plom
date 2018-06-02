import os,json
from testspecification import TestSpecification
from collections import defaultdict

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

def checkMarked(n):
    if(n not in groupImagesMarked):
        print("\tTotally unmarked")
        return(False)
    flag=True
    for pg in range(1,spec.getNumberOfGroups()+1):
        pgs = str(pg)
        if( pgs not in groupImagesMarked[n] ):
            flag=False

    if(flag==False):
        print("\tPartially marked")
    return(flag)

def checkIDed(n):
    print("\tID image {}".format(examsGrouped[n][0]), end='')
    if(n not in examsIDed):
        print("\tNo ID")
        return(False)
    else:
        print("\tID = ", examsIDed[n][1:3])
        return(True)

def checkExam(n):
    global examsIDed
    global groupImagesMarked
    print("##################\nExam {}".format(n))
    if( checkIDed(n) and checkMarked(n) ):
        print("\tComplete - build front page and reassemble.")
        return(True)
    else:
        return(False)

def writeExamsCompleted():
    fh = open("../resources/examsCompleted.json",'w')
    fh.write( json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()

spec = TestSpecification()
spec.readSpec()

readExamsGrouped()
readExamsIDed()
examScores=defaultdict(list)
readGroupImagesMarked()

examsCompleted={}
for n in sorted(examsGrouped.keys()):
    examsCompleted[n]=checkExam(n)

writeExamsCompleted()
