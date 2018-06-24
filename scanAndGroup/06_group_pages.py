from collections import defaultdict
import json
import os
import sys

sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification


def readExamsScanned():
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open('../resources/examsScanned.json') as data_file:
            examsScanned = json.load(data_file)

def readExamsGrouped():
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)

def writeExamsGrouped():
    eg = open("../resources/examsGrouped.json", 'w')
    eg.write(json.dumps(examsGrouped, indent=2, sort_keys=True))
    eg.close()

def groupTest(t):
    examsGrouped[t] = []
    ts = str(t)
    montCommand = "montage -quiet"
    for p in spec.IDGroup:
        ps = str(p)
        v = 1
        montCommand += " page_{:s}/version_{:d}/t{:s}p{:s}v{:d}.png".format(ps.zfill(2), v, ts.zfill(4), ps.zfill(2), v)
    montCommand += " -border 5 -geometry +1+{:d}".format(len(spec.IDGroup))
    montCommand += " ../readyForMarking/idgroup/t{:s}idg.png\n".format(ts.zfill(4))

    examsGrouped[t].append("t{:s}idg".format(ts.zfill(4)))
    for k in range(1, spec.getNumberOfGroups()+1):
        montCommand += "montage -quiet"
        pg = spec.PageGroups[k]
        for p in pg:
            ps = str(p)
            v = examsScanned[ts][ps][0]
            montCommand += " page_{:s}/version_{:d}/t{:s}p{:s}v{:d}.png".format(ps.zfill(2), v, ts.zfill(4), ps.zfill(2), v)
        montCommand += " -border 5 -tile {:d}x1 -geometry +1+{:d}".format(len(pg), len(pg))
        montCommand += " ../readyForMarking/group_{:s}/version_{:d}/t{:s}g{:s}v{:d}.png\n".format(str(k).zfill(2), v, ts.zfill(4), str(k).zfill(2), v)
        examsGrouped[t].append("t{:s}g{:s}v{:d}".format(ts.zfill(4), str(k).zfill(2), v))
    return montCommand

def checkTest(t):
    missing = []
    for p in range(1,spec.Length+1):
        if str(p) not in examsScanned[t]:
            missing.append(p)
    if missing:
        print(">> Test {:s} is missings pages".format(t), missing)
        return False
    else:
        print("Test {:s} is complete, ready to group pages".format(t))
        return True

def checkTests():
    readyToGroup = []
    for t in examsScanned:
        if checkTest(t):
            readyToGroup.append(t)

    commandList = ""
    for t in readyToGroup:
        if t in examsGrouped:
            print(">> Exam {:s} already grouped.".format(t))
        else:
            commandList += groupTest(t)
    os.chdir("decodedPages")
    fh = open("commandlist.txt", "w")
    fh.write(commandList)
    fh.close()
    os.system("parallel --bar < commandlist.txt")
    os.system("rm commandlist.txt")
    os.chdir("../")

spec = TestSpecification()
spec.readSpec()

examsScanned = defaultdict(dict)
examsGrouped = defaultdict(list)

readExamsScanned()
readExamsGrouped()
checkTests()
writeExamsGrouped()
