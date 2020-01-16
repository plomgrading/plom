#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import glob
import os
import shutil
import shlex
import subprocess
import sys

sys.path.append("..")  # this allows us to import from ../resources
from resources.testspecification import TestSpecification


def buildDirectories():
    """Build the directories that the scan scripts need"""
    # the list of directories. Might need updating.
    lst = [
        "scannedExams/alreadyProcessed",
        "scannedExams/png",
        "pageImages",
        "pageImages/alreadyProcessed",
        "pageImages/problemImages",
        "decodedPages",
        "discardedPages",
        "extraPages",
        "readyForMarking",
        "readyForMarking/idgroup/",
    ]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass
    # For each page/version we need a page/version dir
    # in decoded pages
    for p in range(1, spec.Length + 1):
        for v in range(1, spec.Versions + 1):
            dir = "decodedPages/page_{:s}/version_{:d}".format(str(p).zfill(2), v)
            os.makedirs(dir, exist_ok=True)
    # For each pagegroup/version we need a pg/v dir
    # in readformarking. the image server reads from there.
    for pg in range(1, spec.getNumberOfGroups() + 1):
        for v in range(1, spec.Versions + 1):
            dir = "readyForMarking/group_{:s}/version_{:d}".format(str(pg).zfill(2), v)
            os.makedirs(dir, exist_ok=True)


def processFileToPng(fname):
    """Convert each page of pdf into png using ghostscript"""
    scan, fext = os.path.splitext(fname)
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = scan.replace(" ", "_")
    cmd = [
        "gs",
        "-dNumRenderingThreads=4",
        "-dNOPAUSE",
        "-sDEVICE=png256",
        "-o",
        "./png/" + safeScan + "-%d.png",
        "-r200",
        fname,
    ]
    subprocess.run(cmd, check=True)


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
        with open("./commandlist.txt", "w") as fh:
            # build list of mogrify commands to simple gamma shift
            for fn in glob.glob("*.png"):
                fh.write("mogrify -quiet -gamma 0.5 -quality 100 " + fn + "\n")
        # run the command list through parallel then delete
        cmd = shlex.split("parallel --bar -a commandlist.txt")
        subprocess.run(cmd, check=True)
        os.unlink("commandlist.txt")

        # move all the pngs into pageimages directory
        for pngfile in glob.glob("*.png"):
            shutil.move(pngfile, "../../pageImages")
        os.chdir("../")


if __name__ == "__main__":
    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    # Look for pdfs in scanned exams.
    counter = 0
    for fname in os.listdir("./scannedExams"):
        if fname.endswith(".pdf"):
            counter = counter + 1
    # If there are some then process them else return a warning.
    if not counter == 0:
        processScans()
        print("Successfully converted scans to page images")
    else:
        print("Warning: please put scanned exams in scannedExams directory")
