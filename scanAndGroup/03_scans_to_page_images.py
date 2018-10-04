import glob
import os
import sys

sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification

def buildDirectories():
    lst = ["scannedExams/alreadyProcessed", "scannedExams/png", "pageImages", "pageImages/alreadyProcessed", "pageImages/problemImages", "decodedPages", "readyForMarking", "readyForMarking/idgroup/"]
    for x in lst:
        os.system("mkdir -p "+x)

    for p in range(1, spec.Length+1):
        for v in range(1, spec.Versions+1):
            os.system("mkdir -p decodedPages/page_{:s}/version_{:d}".format(str(p).zfill(2), v))

    for pg in range(1, spec.getNumberOfGroups()+1):
        for v in range(1, spec.Versions+1):
            os.system("mkdir -p readyForMarking/group_{:s}/version_{:d}".format(str(pg).zfill(2), v))


def processFileToPng(fname):
    scan, fext = os.path.splitext(fname)
    commandstring = "gs -dNumRenderingThreads=4 -dNOPAUSE -sDEVICE=png256  -o ./png/" +scan+"-%d.png -r200 "+fname
    os.system(commandstring)

def processScans():
    os.chdir("./scannedExams/")

    if not os.path.exists("png"):
        os.makedirs("png")

    for fname in glob.glob("*.pdf"):
        processFileToPng(fname)
        os.system("mv " + fname + " ./alreadyProcessed/"+fname)

        os.chdir("./png/")
        fh = open("./commandlist.txt", "w")
        for fn in glob.glob("*.png"):
            fh.write("mogrify -quiet -gamma 0.5 -quality 100 "+fn+"\n")
        fh.close()

        os.system("parallel --bar <commandlist.txt")
        os.system("rm commandlist.txt")
        os.system("mv *.png ../../pageImages")
        os.chdir("../")


counter = 0

for fname in os.listdir('./scannedExams'):
    if fname.endswith('.pdf'):
        counter = counter + 1

if not counter == 0:

    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    processScans()
    print("successful scanned to page")
else:
    print("warning: please put scanned exams in scannedExams directory")
