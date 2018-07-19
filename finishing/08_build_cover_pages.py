import os,json
from testspecification import TestSpecification
from collections import defaultdict

def readExamsCompleted():
    global examsCompleted
    if(os.path.exists("../resources/examsCompleted.json")):
        with open('../resources/examsCompleted.json') as data_file:
            examsCompleted = json.load(data_file)

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

def extractMarks(n):
    for pg in range(1,spec.getNumberOfGroups()+1):
        pgs = str(pg)
        v = groupImagesMarked[n][pgs][0]
        examScores[n].append([pg, v, groupImagesMarked[n][pgs][1]])

def buildCoverPage(n):
    arg = []
    sname = examsIDed[n][2]
    sid = examsIDed[n][1]
    arg.append(int(n))
    arg.append(sname)
    arg.append(int(sid))

    total = 0
    maxPossible = 0
    for x in examScores[n]:
        total += x[2]
        maxPossible += spec.Marks[x[0]]
        # print("Group {} / version {} = {} out of {}".format(x[0], x[1], x[2], spec.Marks[x[0]]))
        arg.append([x[0], x[1], x[2], spec.Marks[x[0]]])

    return("python3 coverPageBuilder.py \"{}\"\n".format(arg))

os.system('mkdir -p reassembled')
os.system('mkdir -p coverPages')

spec = TestSpecification()
spec.readSpec()

examsCompleted={}
examScores=defaultdict(list)

readExamsCompleted()
readExamsIDed()
readGroupImagesMarked()

fh = open("./commandlist.txt","w")
for n in sorted(examsCompleted.keys()):
    s = "" + n
    if(examsCompleted[n]==True):
        nLength = len(n)
        diff = 4 - nLength
        for d in range(0, diff):
            s = "0" + s

        if not os.path.isfile("./coverPages/cover_{}.pdf".format(s)):
            extractMarks(n)
            fh.write( buildCoverPage(n) )
            fh.write( buildCoverPage(n) )
fh.close()
os.system("parallel --bar <commandlist.txt")
os.system("rm commandlist.txt")
