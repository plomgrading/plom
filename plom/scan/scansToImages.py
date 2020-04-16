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
import math
import random
import tempfile

import toml
from tqdm import tqdm
import fitz
from PIL import Image

from plom import PlomImageExtWhitelist

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


def processFileToBitmaps(fname):
    """Extract/convert each page of pdf into bitmap.

    We have various ways to do this, in rough order of preference:
      1. Extract a scanned bitmap "as-is"
      2. Render the page with PyMuPDF
      3. Render the page with Ghostscript

    For extracting the scanned data as is, we must be careful not to
    just grab any image off the page (for example, it must be the only
    image on the page, and it must not have any annotations on top of
    it).  There are various other conditions; if any of them fail, we
    fall back on rendering with PyMuPDF.

    If the above fail, we fall back on calling Ghostscript as a
    subprocess (the `gs` binary).  NOT IMPLEMENTED YET.

    NOT IMPLEMENTED YET: You can force one of these...
    """

    scan, fext = os.path.splitext(fname)
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = scan.replace(" ", "_")

    doc = fitz.open(fname)

    # 0:9 -> 10 pages -> 2 digits
    zpad = math.floor(math.log10(len(doc))) + 1

    for p in doc:
        basename = "{}-{:0{width}}".format(safeScan, p.number + 1, width=zpad)

        ok_extract = True
        msgs = []

        # Any of these might indicate something more complicated than a scan
        if p.getLinks():
            msgs.append("Has links")
            ok_extract = False
        if list(p.annots()):
            msgs.append("Has annotations")
            ok_extract = False
        if list(p.widgets()):
            msgs.append("Has fillable forms")
            ok_extract = False
        # TODO: which is more expensive, this or getImageList?
        if p.getText("text"):
            msgs.append("Has text")
            ok_extract = False

        if ok_extract:
            r, d = extractImageFromFitzPage(p, doc)
            if not r:
                msgs.append(d)
            else:
                print(
                    '{}: Extracted "{}" from single-image page w={} h={}'.format(
                        basename, d["ext"], d["width"], d["height"]
                    )
                )
                if d["ext"] in PlomImageExtWhitelist:
                    outname = os.path.join("scanPNGs", basename + "." + d["ext"])
                    with open(outname, "wb") as f:
                        f.write(d["image"])
                else:
                    outname = os.path.join("scanPNGs", basename + ".png")
                    with tempfile.NamedTemporaryFile() as g:
                        with open(g.name, "wb") as f:
                            f.write(d["image"])
                        print("  Cowardly transcoding to png (TODO)")
                        subprocess.check_call(["convert", g.name, outname])
                continue

        z = 2.78  # approx match ghostscript's -r200
        # TODO: random sizes for testing
        #z = random.uniform(1, 5)
        print("{}: Fitz render z={:4.2f}. {}".format(basename, z, "; ".join(msgs)))
        pix = p.getPixmap(fitz.Matrix(z, z), annots=True)
        if random.uniform(0, 1) < 0.5:
            outname = os.path.join("scanPNGs", basename + ".png")
            pix.writeImage(outname)
        else:
            outname = os.path.join("scanPNGs", basename + ".jpg")
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # TODO: temporarily lowered the quality to very poor: change back to 94 later.
            img.save(outname, "JPEG", quality=4, optimize=True)


def extractImageFromFitzPage(page, doc):
    """Extract a single image from a fitz page or return False.

    Args:
        page: a page of a fitz document.
        doc: fitz doc containing `page`.

    Returns:
        True/False: whether this page contains nothing but a single image
        msg or dict: if False, a msg about what happened, if True a dict
            The dict has at least the fields `width`, `height`, `image`
            and `ext`.  `d["image"]` is the raw binary data.
    """

    imlist = page.getImageList()
    if len(imlist) != 1:
        return False, "More than one image"

    d = doc.extractImage(imlist[0][0])
    # TODO: log.debug this:
    #print("  " + "; ".join(["{}: {}".format(k, v) for k, v in d.items() if not k == "image"]))
    width = d.get("width")
    height = d.get("height")
    if not (width and height):
        return False, "Extracted, but no size information"

    if width < 600 or height < 800:
        # TODO: log.warn?  Rendering unlikely to help
        # unless its a small image centered on a big page
        return False, "Extracted, but below minimum size"

    if d["smask"] != 0:
        return False, "Extracted, but had some kind of mask"

    return True, d


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
processFileToPng = processFileToBitmaps


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

    # TODO: maybe tiff as well?  Not jpeg: not anything lossy!
    print("Gamma shift the PNG images")
    # list and len bit crude here: more pythonic to leave as iterator?
    stuff = list(glob.glob("*.png"))
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(gamma_adjust, stuff), total=N))
    # Pool does this loop, but in parallel
    # for x in glob.glob("*.png"):
    #     gamma_adjust(x)

    # move all the images into pageimages directory
    fileList = []
    for ext in PlomImageExtWhitelist:
        fileList.extend(glob.glob("*.{}".format(ext)))
    for file in fileList:
        shutil.move(file, os.path.join("..", "pageImages"))
    os.chdir("..")


# TODO: to ease with debugging/experimenting
if __name__ == "__main__":
    #processFileToPng_w_ghostscript("testThis.pdf")
    processFileToBitmaps("testThis.pdf")
    processFileToBitmaps("realscan.pdf")
