from testspecification import TestSpecification
import sys, os, glob

def buildDirectories():
    lst = ["scannedExams/alreadyProcessed", "scannedExams/png", "pageImages", "pageImages/alreadyProcessed", "pageImages/problemImages", "decodedPages", "readyForGrading", "readyForGrading/idgroup/"]
    for x in lst:
        os.system("mkdir -p "+x)

    for p in range(1,spec.Length+1):
        for v in range(1,spec.Versions+1):
            os.system("mkdir -p decodedPages/page_{:s}/version_{:d}".format(str(p).zfill(2),v) )

    for pg in range(1, spec.getNumberOfGroups()+1):
        for v in range(1,spec.Versions+1):
            os.system("mkdir -p readyForGrading/group_{:s}/version_{:d}".format(str(pg).zfill(2),v) )


def processFileToPng(fname):
    scan,fext = os.path.splitext(fname)
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
        fh = open("./commandlist.txt","w")
        for fname in glob.glob("*.png"):
            fh.write("mogrify -gamma 0.5 -quality 100 "+fname+"\n");
        fh.close()

        os.system("parallel --bar <commandlist.txt")
        os.system("rm commandlist.txt")
        os.system("mv *.png ../../pageImages")


spec = TestSpecification()
spec.readSpec()
buildDirectories()
processScans()
