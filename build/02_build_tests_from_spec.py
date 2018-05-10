from testspecification import TestSpecification
from random import randint
import json
import os
from collections import defaultdict

exams=defaultdict(dict)

def buildIDPages(t,idpages):
    for p in idpages:
        exams[t][p]=1 #ID pages are always version1

def buildGroup(t, pageTuple, fcr, V, v):
    if(fcr=='f' or fcr=='i'): #fixed and id pages always version 1
        v=1
    elif(fcr=='r'): #pick one at random
        v=randint(1,V)
    else: #cycle
        v+=1
        if(v>V):
            v=1
    for p in pageTuple:
        exams[t][p]=v

    return(v)

def buildExams(spec):
    npg = spec.getNumberOfGroups()
    ver = [0 for x in range( npg+1 )] #keep track of version of given page group in given exam so can compute cycling versions.
    for t in range(1, spec.Tests+1):
        for k in range(1, npg+1): #runs from 1,2,...
            ver[k] = buildGroup(t, spec.PageGroups[k], spec.FixCycleRandom[k], spec.Versions, ver[k])
            print("Test {} group {} is {} and set to {} = version {}".format(t, k, spec.PageGroups[k], spec.FixCycleRandom[k], ver[k]))
        buildIDPages(t, spec.IDGroup)

def buildDirectories():
    lst = ["examsToBuild", "examsToPrint"]
    for x in lst:
        os.system("mkdir -p "+x)

def buildTexFile(t):
    fname = "examsToBuild/test_{:s}.tex".format( str(t).zfill(4) );
    fh = open(fname,"w")
    fh.write("\\input{../../resources/head.tex}\n")
    fh.write("\\begin{document}\n")

    for p in sorted(exams[t].keys()):
        v=exams[t][p]
        if(p%2==0):
            fh.write( '\\markItEven{{{:s}}}{{{:s}}}{{{:d}}}{{{:s}}}\n'.format(str(t).zfill(4), str(p).zfill(2), v, spec.Name) )
        else:
            fh.write( '\\markItOdd{{{:s}}}{{{:s}}}{{{:d}}}{{{:s}}}\n'.format(str(t).zfill(4), str(p).zfill(2), v, spec.Name) )

    fh.write("\\end{document}\n")
    fh.close();

def buildTexFiles():
    os.system("mkdir -p examsToBuild")
    for t in exams.keys():
        buildTexFile(t)

def buildCommandList():
    fh = open("./examsToBuild/commandlist.txt","w")
    for t in exams.keys():
        fh.write("pdflatex ./test_{:s}.tex; pdflatex ./test_{:s}.tex\n".format( str(t).zfill(4), str(t).zfill(4) ) );
    fh.close()

def doCommandList():
    os.chdir("examsToBuild")
    os.system("parallel <commandlist.txt")
    os.system("mv test_*.pdf ../examsToPrint/")
    os.system("rm *.log *.aux")
    os.chdir("../")

def writeExamLog():
    elFH = open("../resources/examsProduced.json",'w')
    elFH.write( json.dumps(exams, indent=2, sort_keys=True))
    elFH.close()



spec = TestSpecification()
spec.readSpec()
buildDirectories()
buildExams(spec)
buildTexFiles()
buildCommandList()
doCommandList()
writeExamLog()
