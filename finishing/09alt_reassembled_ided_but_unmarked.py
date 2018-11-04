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

def imageList(n):
    imgl = []
    imgl.append( "../scanAndGroup/readyForMarking/idgroup/{}.png".format(examsGrouped[n][0]) )
    for pg in range(spec.getNumberOfGroups()):
        v = examsGrouped[n][pg+1][1:][-1] #version is last digit of the code.
        imgl.append( "../scanAndGroup/readyForMarking/group_{}/version_{}/{}.png".format(str(pg+1).zfill(2), v, examsGrouped[n][pg+1]) )
    return(imgl)

os.system('mkdir -p reassembled_ID_but_not_marked')

spec = TestSpecification()
spec.readSpec()

examsIDed={}
readExamsIDed()
readExamsGrouped()

fh = open("./commandlist.txt","w")
for n in sorted(examsIDed.keys()):
    fh.write( "python3 testReassembler_only_ided.py {} \"{}\"\n".format(examsIDed[n][1], imageList(n)))
fh.close()
os.system("parallel --bar <commandlist.txt")
os.system("rm commandlist.txt")
