import os, glob, json
import re
from collections import defaultdict

from testspecification import TestSpecification


def decodeQRs():
    os.chdir("./pageImages/")
    fh = open("commandlist.txt","w")
    for fname in glob.glob("*.png"):
        if( (not os.path.exists(fname+".qr")) or (os.path.getsize(fname+".qr") == 0) ):
            fh.write("python3 ../extract_qr_and_orient.py {}\n".format(fname))
    fh.close()

    os.system("parallel < commandlist.txt")
    os.system("rm commandlist.txt")
    os.chdir("../")

def readExamsProduced():
    global examsProduced
    with open('../resources/examsProduced.json') as data_file:
        examsProduced = json.load(data_file)

def readExamsScanned():
    global examsScanned
    if(os.path.exists("../resources/examsScanned.json")):
        with open('../resources/examsScanned.json') as data_file:
            examsScanned = json.load(data_file)

def writeExamsScanned():
    es = open("../resources/examsScanned.json",'w')
    es.write( json.dumps(examsScanned, indent=2, sort_keys=True))
    es.close()

def checkQRsValid():
    #valid lines are either
    #  "QR-Code:tXpYvZ" or  "QR-Code:N:X"
    patternCode = re.compile("QR-Code:(t\d+)(p\d+)(v\d+)")
    patternName = re.compile("QR-Code:N.\w+")
    os.chdir("pageImages/")
    for fname in glob.glob("*.qr"):
        fin = open(fname,"r")
        lines=[];
        codeFlag=0; nameFlag=0
        for line in fin:
            line = line.rstrip("\n")
            lines.append(line)
            if(patternName.match(line)):
                nameFlag += 1
                testName = line[10:]
            if(patternCode.match(line)):
                code = re.split("\D", line[8:] ) #valid line will be "QR-Code:tXpYvZ"
                codeFlag += 1

        if(nameFlag==1 and codeFlag==1 and testName == spec.Name):
            # Convert X,Y,Z to ints
            examsScannedNow[int(code[1])][int(code[2])]=(int(code[3]),fname[:-3])
        else:
            print("A problem with codes in {} and testname {}".format(fname, testName) )
            os.system("mv {:s} problemImages/".format(fname))
            os.system("mv {:s} problemImages/".format(fname[:-3]))

    os.chdir("../")

def validateQRsAgainstProduction():
    os.chdir("./pageImages")
    for t in examsScannedNow.keys():
        ts=str(t) #for json keys
        for p in examsScannedNow[t].keys():
            ps=str(p) #for json keys
            v=examsScannedNow[t][p][0];
            fn=examsScannedNow[t][p][1]
            if( examsProduced[ts][ps]==v ):
                print("Valid scan of t{:s} p{:s} v{:d} from file {:s}".format(ts,ps,v,fn) )
            else:
                print(">> Mismatch between exam scanned and exam produced")
                print(">> Produced t{:s} p{:s} v{:d}".format(ts, ps, examsProduced[ts][ps]) )
                print(">> Scanned t{:s} p{:s} v{:d} from file {:s}".format(ts, ps, v, fn) )
                print(">> Moving problem files to problemImages")
                os.system("mv "+fn+"* problemImages/")
    os.chdir("../")

def addCurrentScansToExamsScanned():
    os.chdir("./pageImages")
    copyme=""; moveme=""
    for t in examsScannedNow.keys():
        ts=str(t) #for json keys
        for p in examsScannedNow[t].keys():
            ps=str(p) #for json keys
            v=examsScannedNow[t][p][0]
            fn=examsScannedNow[t][p][1]

            if(ps in examsScanned[ts]): #check file matches
                print(">> Have already scanned t{:s}p{:s}v{:d} in file {:s}".format(ts,ps,v,fn))
                print(">> Will overwrite with new version")
                examsScanned[ts][ps]=examsScannedNow[t][p]
            else: #add to the already scanned list
                examsScanned[ts][ps]=examsScannedNow[t][p]
                copyme += "cp {:s} ../decodedPages/page_{:s}/version_{:s}/t{:s}p{:s}v{:s}.png\n".format(fn,str(p).zfill(2), str(v), str(t).zfill(4),str(p).zfill(2),str(v))
                moveme += "mv {:s}* ./alreadyProcessed\n".format(fn)

    os.system(copyme)
    os.system(moveme)
    os.chdir("../")

examsProduced={}
examsScanned=defaultdict(dict)
examsScannedNow=defaultdict(dict)

spec = TestSpecification()
spec.readSpec()

readExamsProduced()
readExamsScanned()
decodeQRs()
checkQRsValid()
validateQRsAgainstProduction()
addCurrentScansToExamsScanned()
writeExamsScanned()
