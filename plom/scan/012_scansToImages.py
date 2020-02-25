#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import glob
import hashlib
import os
import shutil
import subprocess
import sys
import toml
from multiprocessing import Pool
from tqdm import tqdm

# TODO: make some common util file to store all these names?
archivedir = "archivedPDFs"


def buildDirectories():
    """Build the directories that this scripts needs"""
    # the list of directories. Might need updating.
    os.makedirs("scannedExams", exist_ok=True)
    os.makedirs("pageImages", exist_ok=True)
    os.makedirs(os.path.join("pageImages", "problemImages"), exist_ok=True)
    os.makedirs(archivedir, exist_ok=True)


def archivePDF(fname):
    md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
    # TODO: is ".." portable?  maybe we should keep some absolute paths handy
    shutil.move(fname, os.path.join("..", archivedir))
    # open the existing archive if it is there
    arcName = os.path.join("..", archivedir, "archive.toml")
    if os.path.isfile(arcName):
        arch = toml.load(arcName)
    else:
        arch = {}
    arch[md5] = fname
    # now save it
    with open(arcName, "w+") as fh:
        toml.dump(arch, fh)


def isInArchive(fname):
    arcName = os.path.join("..", archivedir, "archive.toml")
    if not os.path.isfile(arcName):
        return [False]
    arch = toml.load(arcName)
    md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
    if md5 in arch:
        return [True, arch[md5]]
    return [False]


def processFileToPng(fname):
    """Convert each page of pdf into png using ghostscript"""
    scan, fext = os.path.splitext(fname)
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = scan.replace(" ", "_")
    try:
        subprocess.run(
            [
                "gs",
                "-dNumRenderingThreads=4",
                "-dNOPAUSE",
                "-sDEVICE=png256",
                "-o",
                os.path.join("png", safeScan + "-%d.png"),
                "-r200",
                fname,
            ],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    except subprocess.CalledProcessError as suberror:
        print("Error running gs: {}".format(suberror.stdout.decode("utf-8")))


def gamma_adjust(fn):
    """Apply a simple gamma shift to an image"""
    subprocess.run(
        ["mogrify", "-quiet", "-gamma", "0.5", "-quality", "100", fn],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


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
    os.chdir("scannedExams")
    os.makedirs("png", exist_ok=True)
    # look at every pdf file
    for fname in glob.glob("*.pdf"):
        # check if fname is in archive (by checking md5sum)
        tf = isInArchive(fname)
        if tf[0]:
            print(
                "WARNING - {} is in the PDF archive - we checked md5sum - it the same as file {}. It will not be processed.".format(
                    fname, tf[1]
                )
            )
            continue

        # process the file into png page images
        processFileToPng(fname)
        # archive the scan PDF
        archivePDF(fname)
        # go into png directory
        os.chdir("png")

        # Gamma shift the images
        # list and len bit crude here: more pythonic to leave as iterator?
        stuff = list(glob.glob("*.png"))
        N = len(stuff)
        with Pool() as p:
            r = list(tqdm(p.imap_unordered(gamma_adjust, stuff), total=N))
        # Pool does this loop, but in parallel
        # for x in glob.glob("*.png"):
        #     gamma_adjust(x)

        # move all the pngs into pageimages directory
        for pngfile in glob.glob("*.png"):
            shutil.move(pngfile, os.path.join("..", "..", "pageImages"))
        os.chdir("..")


if __name__ == "__main__":
    # Look for pdfs in scanned exams.
    counter = 0
    for fname in os.listdir("scannedExams"):
        if fname.endswith(".pdf"):
            counter = counter + 1
    # If there are some then process them else return a warning.
    if not counter == 0:
        buildDirectories()
        processScans()
        print("Successfully converted scans to page images")
        sys.exit(0)
    else:
        print("Warning: please put scanned exams in scannedExams directory")
        sys.exit(1)
