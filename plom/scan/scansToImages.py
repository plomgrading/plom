__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import glob
import hashlib
import os
import shutil
import subprocess
from multiprocessing import Pool
import random

import toml
from tqdm import tqdm
import fitz
from PIL import Image


# TODO: make some common util file to store all these names?
archivedir = "archivedPDFs"


def archivePDF(fname):
    md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
    # TODO: is ".." portable?  maybe we should keep some absolute paths handy
    shutil.move(fname, archivedir)
    # open the existing archive if it is there
    arcName = os.path.join(archivedir, "archive.toml")
    if os.path.isfile(arcName):
        arch = toml.load(arcName)
    else:
        arch = {}
    arch[md5] = fname
    # now save it
    with open(arcName, "w+") as fh:
        toml.dump(arch, fh)


def isInArchive(fname):
    arcName = os.path.join(archivedir, "archive.toml")
    if not os.path.isfile(arcName):
        return [False]
    arch = toml.load(arcName)
    md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
    if md5 in arch:
        return [True, arch[md5]]
    return [False]


def processFileToBitmap_w_fitz(fname):
    """Convert each page of pdf into bitmap using fitz"""

    scan, fext = os.path.splitext(fname)
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = scan.replace(" ", "_")

    doc = fitz.open(fname)

    for p in doc:
        basename = "{}-{}".format(safeScan, p.number + 1)
        outname = "{}.png".format(basename)
        outname = os.path.join("scanPNGs", outname)

        ok_extract = True
        msgs = []

        # Want to be careful we don't lose student annotations
        # TODO: its not so bad, see annots=True in getPixmap...
        if p.getLinks():
            msgs.append("Has links")
            ok_extract = False
        if list(p.annots()):
            msgs.append("Has annotations")
            ok_extract = False
        if list(p.widgets()):
            msgs.append("Has fillable forms")
            ok_extract = False

        if ok_extract:
            imlist = p.getImageList()
            if len(imlist) == 1:
                msgs.append("Extracted from single-image page")
                d = doc.extractImage(imlist[0][0])
                # TODO: log.debug this:
                #print("  " + "; ".join(["{}: {}".format(k, v) for k, v in d.items() if not k == "image"]))
                width = d.get("width")
                height = d.get("height")
                msgs[-1] += " w={} h={}".format(width, height)
                if width and height:
                    if width < 600 or height < 800:
                        # TODO: log.warn?  Rendering unlikely to help
                        # unless its a small image centered on a big page
                        ok_extract = False
                        msgs.append("Below minimum size")
                else:
                    ok_extract = False
                    msgs.append("No size information")

                if d["smask"] != 0:
                    ex_extract = False
                    msgs.append("Extracted, but had some kind of mask")

                if ok_extract:
                    msgs.append("Cowardly transcoding to png")
                    print("{}: {}".format(basename, "; ".join(msgs)))
                    rawname = "{}-raw.{}".format(basename, d["ext"])
                    with open(rawname, "wb") as f:
                        f.write(d["image"])
                    subprocess.check_call(["convert", rawname, outname])
                    os.unlink(rawname)
                    continue

        z = 2.78  # approx match ghostscript's -r200
        # TODO: random sizes for testing
        z = random.uniform(1, 5)
        print("{}: Fitz render z={:4.2f}. {}".format(basename, z, "; ".join(msgs)))
        pix = p.getPixmap(fitz.Matrix(z, z))
        pix.writeImage(outname)
        # TODO: experiment with jpg: generate both and see which is smaller?
        #img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        #img.save(outname.replace('.png', '.jpg'), "JPEG", quality=94, optimize=True)


def processFileToPng_w_ghostscript(fname):
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
                os.path.join("scanPNGs", safeScan + "-%d.png"),
                "-r200",
                fname,
            ],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    except subprocess.CalledProcessError as suberror:
        print("Error running gs: {}".format(suberror.stdout.decode("utf-8")))


#processFileToPng = processFileToPng_w_ghostscript
processFileToPng = processFileToBitmap_w_fitz


def gamma_adjust(fn):
    """Apply a simple gamma shift to an image"""
    subprocess.run(
        ["mogrify", "-quiet", "-gamma", "0.5", "-quality", "100", fn],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


def processScans(fname):
    """ Process given fname into png pageimages in the png subdir
    Then move the processed pdf into alreadyProcessed
    so as to avoid duplications.
    Do a small amount of post-processing of the pngs
    A simple gamma shift to leave white-white but make everything
    else darker. Improves images when students write in
    very light pencil.
    """

    # check if fname is in archive (by checking md5sum)
    tf = isInArchive(fname)
    if tf[0]:
        print(
            "WARNING - {} is in the PDF archive - we checked md5sum - it the same as file {}. It will not be processed.".format(
                fname, tf[1]
            )
        )
        return

    # process the file into png page images
    processFileToPng(fname)
    # archive the scan PDF
    archivePDF(fname)
    # go into png directory
    os.chdir("scanPNGs")

    print("Gamma shift the images")
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
        shutil.move(pngfile, os.path.join("..", "pageImages"))
    os.chdir("..")


# TODO: to ease with debugging/experimenting
if __name__ == "__main__":
    #processFileToPng_w_ghostscript("testThis.pdf")
    processFileToBitmap_w_fitz("realscan.pdf")
    processFileToBitmap_w_fitz("testThis.pdf")
