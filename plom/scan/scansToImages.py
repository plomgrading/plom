__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import glob
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from multiprocessing import Pool
import math
import random
import tempfile
import warnings

import toml
from tqdm import tqdm
import fitz
from PIL import Image
import jpegtran

from plom import PlomImageExtWhitelist
from plom import ScenePixelHeight


# TODO: make some common util file to store all these names?
archivedir = "archivedPDFs"


def archivePDF(fname, hwByQ, hwExtra):
    print("Archiving {}".format(fname))
    md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
    # TODO: is ".." portable?  maybe we should keep some absolute paths handy
    if hwByQ:
        shutil.move(fname, Path(archivedir) / "submittedHWByQ")
    elif hwExtra:
        shutil.move(fname, Path(archivedir) / "submittedHWExtra")
    else:
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


def processFileToBitmaps(bundleDir, fname):
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

    destDir = os.path.join(bundleDir, "scanPNGs")

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
                if d["ext"].lower() in PlomImageExtWhitelist:
                    converttopng = False
                    # Bail on jpeg if dimensions are not multiples of 16.
                    # (could relax: iMCU can also be 8x8, 16x8, 8x16: see PIL .layer)
                    if d["ext"].lower() in ("jpeg", "jpg") and not (
                        d["width"] % 16 == 0 and d["height"] % 16 == 0
                    ):
                        converttopng = True
                        print(
                            "  JPEG dim not mult. of 16; transcoding to PNG to avoid lossy transforms"
                        )
                        # TODO: we know its jpeg, could use PIL instead of `convert` below
                else:
                    converttopng = True
                    print(
                        "  {} format not whitelisted; transcoding to PNG".format(
                            d["ext"]
                        )
                    )

                if not converttopng:
                    outname = os.path.join(destDir, basename + "." + d["ext"])
                    with open(outname, "wb") as f:
                        f.write(d["image"])
                else:
                    outname = os.path.join(destDir, basename + ".png")
                    with tempfile.NamedTemporaryFile() as g:
                        with open(g.name, "wb") as f:
                            f.write(d["image"])
                        subprocess.check_call(["convert", g.name, outname])
                continue

        # looks they use ceil not round so decrease a little bit
        z = (float(ScenePixelHeight) - 0.01) / p.MediaBoxSize[1]
        ## For testing, choose widely varying random sizes
        # z = random.uniform(1, 5)
        print("{}: Fitz render z={:4.2f}. {}".format(basename, z, "; ".join(msgs)))
        pix = p.getPixmap(fitz.Matrix(z, z), annots=True)
        if pix.height != ScenePixelHeight:
            warnings.warn(
                "rounding error: height of {} instead of {}".format(
                    pix.height, ScenePixelHeight
                )
            )

        ## For testing, randomly make jpegs, sometimes of truly horrid quality
        # if random.uniform(0, 1) < 0.4:
        #     outname = os.path.join("scanPNGs", basename + ".jpg")
        #     img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        #     quality = random.choice([4, 94, 94, 94, 94])
        #     img.save(outname, "JPEG", quality=quality, optimize=True)
        #     # random reorient half for debug/test, uses exiftool (Ubuntu: libimage-exiftool-perl)
        #     r = random.choice([None, None, None, 3, 6, 8])
        #     if r:
        #         print("re-orienting randomly {}".format(r))
        #         subprocess.check_call(["exiftool", "-overwrite_original", "-Orientation#={}".format(r), outname])
        #     continue

        # TODO: experiment with jpg: generate both and see which is smaller?
        # (But be careful about "dim mult of 16" thing above.)
        outname = os.path.join(destDir, basename + ".png")
        pix.writeImage(outname)


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
    # print("  " + "; ".join(["{}: {}".format(k, v) for k, v in d.items() if not k == "image"]))
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


# TODO: for debugging, can replace with the older ghostscript
# processFileToBitmaps = processFileToPng_w_ghostscript


def gamma_adjust(fn):
    """Apply a simple gamma shift to an image"""
    subprocess.run(
        ["mogrify", "-quiet", "-gamma", "0.5", fn],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


def normalizeJPEGOrientation(f):
    """Transform image according to its Exif metadata.

    Gives a warning if size not a multiple 16 b/c underlying library
    just quietly mucks up the bottom/right edge:
    https://github.com/jbaiter/jpegtran-cffi/issues/23

    In Plom, we generally transcode jpeg's that are not multiples of 16.
    """
    im = jpegtran.JPEGImage(f)
    if im.exif_orientation:
        if im.width % 16 or im.height % 16:
            warnings.warn(
                '  JPEG image "{}" dims not mult of 16: re-orientations may be lossy'.format(
                    f
                )
            )
        im2 = im.exif_autotransform()
        print(
            '  normalizing "{}" {}x{} to "{}" {}x{}'.format(
                im.exif_orientation,
                im.width,
                im.height,
                im2.exif_orientation,
                im2.width,
                im2.height,
            )
        )
        im2.save(f)


def makeBundleDirectories(fname):
    """Each bundle needs its own subdirectory of pageImages and scanPNGs, so we have to make them.
    """

    scan, fext = os.path.splitext(fname)
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = scan.replace(" ", "_")
    # make directory for that bundle inside scanPNGs
    bundleDir = os.path.join("bundles", safeScan)
    os.makedirs(bundleDir, exist_ok=True)
    # now inside that we need other subdir [pageImages, scanPNGs, decodedPages, unknownPages]
    for dir in ["pageImages", "scanPNGs", "decodedPages", "unknownPages"]:
        os.makedirs(os.path.join(bundleDir, dir), exist_ok=True)

    return bundleDir


def postProcessing(bundleDir):
    """Do the post processing on the files inside bundleDir
    """
    # get current directory, we need to go back there at the end.
    startDir = os.getcwd()
    # now cd into the scanPNGs directory of the current bundle.

    os.chdir(os.path.join(bundleDir, "scanPNGs"))

    print("Normalizing jpeg orientation from Exif metadata")
    stuff = list(glob.glob("*.jpg"))
    stuff.extend(glob.glob("*.jpeg"))
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(normalizeJPEGOrientation, stuff), total=N))

    # TODO: maybe tiff as well?  Not jpeg: not anything lossy!
    print("Gamma shift the PNG images")
    # list and len bit crude here: more pythonic to leave as iterator?
    stuff = list(glob.glob("*.png"))
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(gamma_adjust, stuff), total=N))
    # Pool does this loop, but in parallel
    # for x in glob.glob("..."):
    #     gamma_adjust(x)

    # move all the images into pageimages directory of this bundle
    dest = os.path.join("../pageImages")
    fileList = []
    for ext in PlomImageExtWhitelist:
        fileList.extend(glob.glob("*.{}".format(ext)))
    # move them to pageimages for barcode reading
    for file in fileList:
        shutil.move(file, dest)

    # now cd back to the starting directory
    os.chdir(startDir)


def processScans(PDFs, hwByQ=False, hwLoose=False):
    """Process files into bitmap pageimages and archive the pdf.

    Process each page of a pdf file into bitmaps.  Then move the processed
    pdf into "alreadyProcessed" so as to avoid duplications.

    Do a small amount of post-processing when possible to do losslessly
    (e.g., png).  A simple gamma shift to leave white-white but make
    everything else darker.  Improves images when students write in very
    light pencil.
    """

    for fname in PDFs:
        # check if fname is in archive (by checking md5sum)
        tf = isInArchive(fname)
        if tf[0]:
            print(
                "WARNING - {} is in the PDF archive - we checked md5sum - it the same as file {}. It will not be processed.".format(
                    fname, tf[1]
                )
            )
            continue
        else:
            # PDF is not in archive, so is new bundle.
            # make a directory for it # is of form "bundle/fname/"
            bundleDir = makeBundleDirectories(fname)
            processFileToBitmaps(bundleDir, fname)
            postProcessing(bundleDir)
            # finally archive the PDF
            archivePDF(fname, hwByQ, hwLoose)

    # TODO - sort out homeworks
    # if hwExtra:
    # os.chdir("submittedHWExtra")
    # elif hwByQ:
    # os.chdir("submittedHWByQ")
    # TODO - sort out homework again.
    # # move directly to decodedPages/submittedHWByQ or  Extra - there is no "read" step
    # if hwByQ:
    #     for file in fileList:
    #         shutil.move(
    #             file, os.path.join("..", "..", "decodedPages", "submittedHWByQ")
    #         )
    #     os.chdir(os.path.join("..", ".."))
    # elif hwExtra:
    #     for file in fileList:
    #         shutil.move(
    #             file, os.path.join("..", "..", "decodedPages", "submittedHWExtra")
    #         )
    #     os.chdir(os.path.join("..", ".."))
