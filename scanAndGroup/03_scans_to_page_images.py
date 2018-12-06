import glob
import os
import shutil
import sys
sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification


def buildDirectories():
    """Build the directories that the scan scripts need"""
    # the list of directories. Might need updating.
    lst = ["scannedExams/alreadyProcessed", "scannedExams/png",
           "pageImages", "pageImages/alreadyProcessed",
           "pageImages/problemImages", "decodedPages",
           "readyForMarking", "readyForMarking/idgroup/"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass
    # For each page/version we need a page/version dir
    # in decoded pages
    for p in range(1, spec.Length+1):
        for v in range(1, spec.Versions+1):
            os.system("mkdir -p decodedPages/page_{:s}/version_{:d}".format(str(p).zfill(2), v))
    # For each pagegroup/version we need a pg/v dir
    # in readformarking. the image server reads from there.
    for pg in range(1, spec.getNumberOfGroups()+1):
        for v in range(1, spec.Versions+1):
            os.system("mkdir -p readyForMarking/group_{:s}/version_{:d}".format(str(pg).zfill(2), v))


def processFileToPng(fname):
    """Convert each page of pdf into png using ghostscript"""
    scan, fext = os.path.splitext(fname)
    commandstring = "gs -dNumRenderingThreads=4 -dNOPAUSE -sDEVICE=png256 "\
        "-o ./png/" +scan+"-%d.png -r200 "+fname
    os.system(commandstring)


def processScans():
    """Look in the scanned exams directory
    Process each pdf into png pageimages in the png subdir
    Then move the processed pdf into alreadyProcessed
    so as to avoid duplications.
    Do a small amount of post-processing of the pngs
    A simple gamma shift to leave white-white but make everything
    else darker. Improves images when students write in
    very light pencil.
    """
    # go into scanned exams and create png subdir if needed.
    os.chdir("./scannedExams/")
    if not os.path.exists("png"):
        os.makedirs("png")
    # look at every pdf file
    for fname in glob.glob("*.pdf"):
        # process the file into png page images
        processFileToPng(fname)
        # move file into alreadyProcessed
        shutil.move(fname, "alreadyProcessed")
        # go into png directory
        os.chdir("./png/")
        fh = open("./commandlist.txt", "w")
        # build list of mogrify commands to do
        # each does simple gamma shift to image
        for fn in glob.glob("*.png"):
            fh.write("mogrify -quiet -gamma 0.5 -quality 100 "+fn+"\n")
        fh.close()
        # run the command list through parallel then delete
        os.system("parallel --bar <commandlist.txt")
        os.unlink("commandlist.txt")
        # move all the pngs into pageimages directory
        for pngfile in glob.glob("*.png"):
            shutil.move(pngfile, "../../pageImages")
        os.chdir("../")

# Look for pdfs in scanned exams.
counter = 0
for fname in os.listdir('./scannedExams'):
    if fname.endswith('.pdf'):
        counter = counter + 1
# If there are some then process them else return a warning.
if not counter == 0:
    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    processScans()
    print("Successfully converted scans to page images")
else:
    print("Warning: please put scanned exams in scannedExams directory")
