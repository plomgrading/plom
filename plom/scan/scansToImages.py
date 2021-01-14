# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Andreas Buttenschoen

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from multiprocessing import Pool
import math
import tempfile
import warnings

import toml
from tqdm import tqdm
import fitz
from PIL import Image
import jpegtran

from plom import PlomImageExts
from plom import ScenePixelHeight


# TODO: make some common util file to store all these names?
archivedir = Path("archivedPDFs")


def _archiveBundle(file_name, this_archive_dir):
    """Archive the bundle pdf.

    The bundle.pdf is moved into the appropriate archive directory
    as given by this_archive_dir. The archive.toml file is updated
    with the name and md5sum of that bundle.pdf.
    """
    md5 = hashlib.md5(open(file_name, "rb").read()).hexdigest()
    shutil.move(file_name, this_archive_dir / Path(file_name).name)
    try:
        arch = toml.load(archivedir / "archive.toml")
    except FileNotFoundError:
        arch = {}
    arch[md5] = str(file_name)
    # now save it
    with open(archivedir / "archive.toml", "w+") as fh:
        toml.dump(arch, fh)


def archiveHWBundle(file_name):
    """Archive a hw-pages bundle pdf"""
    print("Archiving homework bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir / "submittedHWByQ")


def archiveLBundle(file_name):
    """Archive a loose-pages bundle pdf"""
    print("Archiving loose-page bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir / "submittedLoose")


def archiveTBundle(file_name):
    """Archive a test-pages bundle pdf"""
    print("Archiving test-page bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir)


def _md5sum_in_archive(filename):
    """Check for a file in the list of archived PDF files.

    Args:
        filename (str): the basename (not path) of a file to search for
            in the archive of PDF files that have been processed.

    Returns:
        None/str: None if not found, else the md5sum.

    Note: Current unused?
    """
    try:
        archive = toml.load(archivedir / "archive.toml")
    except FileNotFoundError:
        return ""
    for md5, name in archive.items():
        if filename == name:
            # if not unique too bad you get 1st one
            return md5


def isInArchive(file_name):
    """
    Check given file by md5sum against archived bundles.

    Returns:
        None/str: None if not found, otherwise filename of archived file
            with the same md5sum.
    """
    try:
        archive = toml.load(archivedir / "archive.toml")
    except FileNotFoundError:
        return None
    md5 = hashlib.md5(open(file_name, "rb").read()).hexdigest()
    return archive.get(md5, None)


def processFileToBitmaps(file_name, dest, do_not_extract=False):
    """Extract/convert each page of pdf into bitmap.

    We have various ways to do this, in rough order of preference:
      1. Extract a scanned bitmap "as-is"
      2. Render the page with PyMuPDF
      3. Render the page with Ghostscript

    Args:
        file_name (str, Path): PDF file from which to extract bitmaps.
        dest (str, Path): where to save the resulting bitmap files.
        do_not_extract (bool): always render, do no extract even if
            it seems possible to do so.

    For extracting the scanned data as is, we must be careful not to
    just grab any image off the page (for example, it must be the only
    image on the page, and it must not have any annotations on top of
    it).  There are various other conditions; if any of them fail, we
    fall back on rendering with PyMuPDF.

    If the above fail, we fall back on calling Ghostscript as a
    subprocess (the `gs` binary).  TODO: NOT IMPLEMENTED YET.
    """
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = Path(file_name).stem.replace(" ", "_")

    doc = fitz.open(file_name)

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

        # TODO: Do later to get more info in prep for future change to default
        if do_not_extract:
            msgs.append("Disabled by flag")
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
                if d["ext"].lower() in PlomImageExts:
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
                        "  {} format not in allowlist: transcoding to PNG".format(
                            d["ext"]
                        )
                    )

                if not converttopng:
                    outname = os.path.join(dest, basename + "." + d["ext"])
                    with open(outname, "wb") as f:
                        f.write(d["image"])
                else:
                    outname = os.path.join(dest, basename + ".png")
                    with tempfile.NamedTemporaryFile() as g:
                        with open(g.name, "wb") as f:
                            f.write(d["image"])
                        subprocess.check_call(["convert", g.name, outname])
                continue

        # looks they use ceil not round so decrease a little bit
        z = (float(ScenePixelHeight) - 0.01) / p.MediaBoxSize[1]
        ## For testing, choose widely varying random sizes
        # z = random.uniform(1, 5)
        print(
            "{}: Fitz render z={:4.2f}. No extract b/c: {}".format(
                basename, z, "; ".join(msgs)
            )
        )
        pix = p.getPixmap(matrix=fitz.Matrix(z, z), annots=True)
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
        outname = os.path.join(dest, basename + ".png")
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
    if len(imlist) > 1:
        return False, "More than one image"
    if len(imlist) == 0:
        return False, "Image List is Empty"

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


def processFileToPng_w_ghostscript(fname, dest):
    """Convert each page of pdf into png using ghostscript"""
    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = Path(fname).stem.replace(" ", "_")
    try:
        subprocess.run(
            [
                "gs",
                "-dNumRenderingThreads=4",
                "-dNOPAUSE",
                "-sDEVICE=png256",
                "-o",
                os.path.join(dest, safeScan + "-%d.png"),
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
        # str to workaround https://github.com/jbaiter/jpegtran-cffi/issues/28
        im2.save(str(f))


def makeBundleDirectories(fname, bundle_dir):
    """Each bundle needs its own subdirectories: make pageImages, scanPNGs, etc.

    Args:
        fname (str, Path): the name of a pdf-file, zip-file or whatever
            from which we create the bundle name.
        bundle_dir (Path): A directory to contain the various
            extracted files, QR codes, uploaded stuff etc.

    Returns:
        None
    """
    # TODO: consider refactor viz scripts/scan and scripts/hwscan which has similar
    for dir in ["pageImages", "scanPNGs", "decodedPages", "unknownPages"]:
        os.makedirs(bundle_dir / dir, exist_ok=True)


def postProcessing(thedir, dest, skip_gamma=False):
    """Do post processing on a directory of scanned bitmaps.

    Args:
        thedir (str, Path): a directory full of bitmaps.
        dest (str, Path): move images here (???).
        skip_gamma_shift (bool): skip the white balancing.
    """
    thedir = Path(thedir)
    dest = Path(dest)

    print("Normalizing jpeg orientation from Exif metadata")
    stuff = list(thedir.glob("*.jpg"))
    stuff.extend(thedir.glob("*.jpeg"))
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(normalizeJPEGOrientation, stuff), total=N))

    if not skip_gamma:
        # TODO: maybe tiff as well?  Not jpeg: not anything lossy!
        print("Gamma shift the PNG images")
        # list and len bit crude here: more pythonic to leave as iterator?
        stuff = list(thedir.glob("*.png"))
        N = len(stuff)
        with Pool() as p:
            r = list(tqdm(p.imap_unordered(gamma_adjust, stuff), total=N))
        # Pool does this loop, but in parallel
        # for x in glob.glob("..."):
        #     gamma_adjust(x)

    fileList = []
    for ext in PlomImageExts:
        fileList.extend(thedir.glob("*.{}".format(ext)))
    # move them to pageimages for barcode reading
    for file in fileList:
        shutil.move(file, dest / file.name)


def processScans(pdf_fname, bundle_dir, skip_gamma=False, skip_img_extract=False):
    """Process files into bitmap pageimages.

    Process each page of a pdf file into bitmaps.

    Do a small amount of post-processing when possible to do losslessly
    (e.g., png).  A simple gamma shift to leave white-white but make
    everything else darker.  Improves images when students write in very
    light pencil.

    Args:
        pdf_fname (str, pathlib.Path): the path to a PDF file.  Used to
            access the file itself.  TODO: is the filename also used for
            anything else by code called by this function?
        bundle_dir (pathlib.Path): the filesystem path to the bundle,
            either as an absolute path or relative the CWD.
        skip_gamma (bool): skip white balancing in post processing.
        skip_img_extract (bool): don't try to extract raw images, just
            render each page.  If `False`, images still may not be
            extracted: there are a variety of sanity checks that must
            pass.

    Returns:
        None
    """
    # TODO: potential confusion local archive versus on server: in theory
    # annot get to local archive unless its uploaded, but what about unknowns, etc?

    # check if fname is in local archive (by checking md5sum)
    prevname = isInArchive(pdf_fname)
    if prevname:
        print(
            "WARNING - {} is in the PDF archive - we checked md5sum - it the same as file {}. It will not be processed.".format(
                pdf_fname, prevname
            )
        )
        return
    makeBundleDirectories(pdf_fname, bundle_dir)
    bitmaps_dir = bundle_dir / "scanPNGs"
    processFileToBitmaps(pdf_fname, bitmaps_dir, skip_img_extract)
    postProcessing(bitmaps_dir, bundle_dir / "pageImages", skip_gamma)
