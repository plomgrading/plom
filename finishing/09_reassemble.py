from collections import defaultdict
import json
import os
import sys
# this allows us to import from ../resources
sys.path.append('..')
from resources.testspecification import TestSpecification


def readExamsGrouped():
    global examsGrouped
    if(os.path.exists("../resources/examsGrouped.json")):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)


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


def imageList(n):
    imgl = ["coverPages/cover_{}.pdf".format(n.zfill(4))]
    imgl.append( "../scanAndGroup/readyForMarking/idgroup/{}.png".format(examsGrouped[n][0]) )
    for pg in range(spec.getNumberOfGroups()):
        imgl.append( "../imageServer/markedPapers/G{}.png".format(examsGrouped[n][pg+1][1:]) )
    return(imgl)


def writeExamsCompleted():
    fh = open("../resources/examsReassembled.json",'w')
    fh.write( json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()


os.system('mkdir -p reassembled')
os.system('mkdir -p frontPages')

spec = TestSpecification()
spec.readSpec()

readExamsCompleted()
readExamsIDed()
readExamsGrouped()
fh = open("./commandlist.txt","w")
for n in sorted(examsCompleted.keys()):
    if(examsCompleted[n]==True):
        fh.write( "python3 testReassembler.py {} \"{}\"\n".format(examsIDed[n][1], imageList(n)))
fh.close()
os.system("parallel --bar <commandlist.txt")
os.system("rm commandlist.txt")
