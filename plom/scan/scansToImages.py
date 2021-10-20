# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Andreas Buttenschoen

from pathlib import Path
import shutil
import subprocess
from multiprocessing import Pool
import math
import tempfile
from warnings import warn

from tqdm import tqdm
import fitz
from PIL import Image

from plom import PlomImageExts
from plom import ScenePixelHeight
from plom.scan.rotate import normalizeJPEGOrientation
from plom.scan.bundle_utils import make_bundle_dir


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

    Returns:
        list: an ordered list of the images of each page.  Each entry
            is a `pathlib.Path`.

    Raises:
        RuntimeError: not a PDF and not something PyMuPDF can open.
        TypeError: not a PDF, but it can be opened by PuMuPDF.
        ValueError: unrealistically tall skinny or very wide pages.

    For extracting the scanned data as is, we must be careful not to
    just grab any image off the page (for example, it must be the only
    image on the page, and it must not have any annotations on top of
    it).  There are various other conditions; if any of them fail, we
    fall back on rendering with PyMuPDF.

    If the above fail, we fall back on calling Ghostscript as a
    subprocess (the `gs` binary).  TODO: NOT IMPLEMENTED YET.
    """
    dest = Path(dest)

    # issue #126 - replace spaces in names with underscores for output names.
    safeScan = Path(file_name).stem.replace(" ", "_")

    doc = fitz.open(file_name)

    if not doc.is_pdf:
        raise TypeError("This does not appear to be a PDF file")
    if doc.is_repaired:
        warn("PyMuPDF had to repair this PDF: perhaps it is damaged in some way?")

    # 0:9 -> 10 pages -> 2 digits
    zpad = math.floor(math.log10(len(doc))) + 1

    files = []
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
                    print(f"  {d['ext']} format not in allowlist: transcoding to PNG")

                if not converttopng:
                    outname = dest / (basename + "." + d["ext"])
                    with open(outname, "wb") as f:
                        f.write(d["image"])
                    files.append(outname)
                else:
                    outname = dest / (basename + ".png")
                    with tempfile.NamedTemporaryFile() as g:
                        with open(g.name, "wb") as f:
                            f.write(d["image"])
                        subprocess.check_call(["convert", g.name, outname])
                    files.append(outname)
                continue

        aspect = p.mediabox_size[0] / p.mediabox_size[1]
        H = ScenePixelHeight
        W = H * aspect
        MINWIDTH = 1024
        MAXHEIGHT = 15999
        MAXWIDTH = 3 * ScenePixelHeight // 2
        assert MINWIDTH < ScenePixelHeight
        # Note logic not same between tall and wide:
        #   * tall: "Safeway receipt", observed from "infinite paper" software
        #   * wide: "fortune cookie", little strip cropped from regular sheet
        # In the tall case, we use extra pixels vertically because there is
        # actually more to resolve.  But I've never seen a wide case that was
        # wider than a landscape sheet of paper.  Also, currently, Client's
        # would display such a thin wide strip at to large a scale.
        if aspect > 1:
            if W > MAXWIDTH:
                # TODO: warn of extreme aspect ratio?  Flag to control this?
                W = MAXWIDTH
                H = W / aspect
                if H < 100:
                    raise ValueError("Scanned a strip too wide and thin?")
        else:
            if W < MINWIDTH:
                W = MINWIDTH
                H = W / aspect
                if H > MAXHEIGHT:
                    H = MAXHEIGHT
                    W = H * aspect
                    if W < 100:
                        raise ValueError("Scanned a long strip of thin paper?")

        # fitz uses ceil (not round) so decrease a little bit
        if W > H:
            z = (float(W) - 0.0001) / p.mediabox_size[0]
        else:
            z = (float(H) - 0.0001) / p.mediabox_size[1]
        ## For testing, choose widely varying random sizes
        # z = random.uniform(1, 5)
        print(f"{basename}: Fitz render z={z:4.2f}. No extract b/c: " + "; ".join(msgs))
        pix = p.get_pixmap(matrix=fitz.Matrix(z, z), annots=True)
        if not (W == pix.width or H == pix.height):
            warn(
                "Debug: some kind of rounding error in scaling image?"
                f" Rendered to {pix.width}x{pix.height} from target {W}x{H}"
            )

        ## For testing, randomly make jpegs, sometimes of truly horrid quality
        # if random.uniform(0, 1) < 0.4:
        #     outname = dest / (basename + ".jpg")
        #     img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        #     quality = random.choice([4, 94, 94, 94, 94])
        #     img.save(outname, "JPEG", quality=quality, optimize=True)
        #     # random reorient half for debug/test, uses exiftool (Ubuntu: libimage-exiftool-perl)
        #     r = random.choice([None, None, None, 3, 6, 8])
        #     if r:
        #         print("re-orienting randomly {}".format(r))
        #         subprocess.check_call(["exiftool", "-overwrite_original", "-Orientation#={}".format(r), outname])
        #     files.append(outname)
        #     continue

        # TODO: experiment with jpg: generate both and see which is smaller?
        # (But be careful about "dim mult of 16" thing above.)
        outname = dest / (basename + ".png")
        pix.writeImage(outname)
        files.append(outname)
    assert len(files) == len(doc), "Expected one image per page"
    return files


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

    imlist = page.get_images()
    if len(imlist) > 1:
        return False, "More than one image"
    if len(imlist) == 0:
        return False, "Image List is Empty"

    d = doc.extract_image(imlist[0][0])
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
    dest = Path(dest)
    try:
        subprocess.run(
            [
                "gs",
                "-dNumRenderingThreads=4",
                "-dNOPAUSE",
                "-sDEVICE=png256",
                "-o",
                dest / (safeScan + "-%d.png"),
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


def process_scans(pdf_fname, bundle_dir, skip_gamma=False, skip_img_extract=False):
    """Process a pdf file into bitmap images of each page.

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
        list: filenames (`pathlib.Path`) in page order, one for each page.
    """
    make_bundle_dir(bundle_dir)
    bitmaps_dir = bundle_dir / "scanPNGs"
    files = processFileToBitmaps(pdf_fname, bitmaps_dir, skip_img_extract)
    postProcessing(bitmaps_dir, bundle_dir / "pageImages", skip_gamma)
    #           ,,,
    #          (o o)
    # -----ooO--(_)--Ooo------
    # hacky myhacker was here!
    # (instead we could rethink postProcessing)
    files = [bundle_dir / "pageImages" / f.name for f in files]
    return files
