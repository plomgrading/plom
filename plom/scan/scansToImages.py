# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Andreas Buttenschoen

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import struct
import subprocess
from multiprocessing import Pool
import random
from warnings import warn
import uuid

from tqdm import tqdm
import exif
import fitz
import PIL
import PIL.ExifTags
import PIL.PngImagePlugin

from plom import __version__
from plom import PlomImageExts
from plom import ScenePixelHeight
from plom.scan.bundle_utils import make_bundle_dir
from plom.scan.rotate import pil_load_with_jpeg_exif_rot_applied


log = logging.getLogger("scan")


def _generate_metadata(bundle_name, bundle_page):
    """Generate new metadata dict for a bitmap."""
    return {
        "PlomVersion": __version__,
        "SourceBundle": str(bundle_name),
        "SourceBundlePosition": str(bundle_page),
        "RandomUUID": str(uuid.uuid4()),
    }


def generate_metadata_str(bundle_name, bundle_page):
    """Generate new metadata for a bitmap as a string."""
    return " ".join(
        f"{k}:{v};" for k, v in _generate_metadata(bundle_name, bundle_page).items()
    )


def generate_png_metadata(bundle_name, bundle_page):
    """Generate new metadata for a bitmap."""
    metadata = PIL.PngImagePlugin.PngInfo()
    for k, v in _generate_metadata(bundle_name, bundle_page).items():
        metadata.add_text(k, v)
    return metadata


def add_metadata_png(filename, bundle_name, bundle_page):
    """Insert metadata into an existing png file.

    Args:
        filename (pathlib.Path/str): name of a png file to edit.
        bundle_name (str): usually the filename of the bundle.
        bundle_page (int): what page of the bundle.

    Returns:
        None

    This is used to write some unique metadata into the PNG file,
    originally to avoid Issue #1573.
    """
    img = PIL.Image.open(filename)
    metadata = generate_png_metadata(bundle_name, bundle_page)
    img.save(filename, pnginfo=metadata)


def add_metadata_jpeg_exif(filename, bundle_name, bundle_page):
    """Insert metadata into an existing jpeg file, via EXIF fields.

    Raises:
        ValueError: known to fail if existing file has a shorter
            ``user_comment`` field.
    """
    im_shell = exif.Image(filename)
    im_shell.set("user_comment", generate_metadata_str(bundle_name, bundle_page))
    with open(filename, "wb") as f:
        f.write(im_shell.get_file())


def add_metadata_jpeg_comment(filename, bundle_name, bundle_page):
    """Insert metadata into an existing jpeg file, by appending comment.

    Args:
        filename (pathlib.Path/str): name of a jpeg file to edit.
        bundle_name (str): usually the filename of the bundle.
        bundle_page (int): what page of the bundle.

    Returns:
        None

    This is used to write some unique metadata into the JPEG file,
    originally to avoid Issue #1573.

    We just append some data onto the end of the file.  As long as it
    starts with the particular byte sequence ``ff fe``, then its a
    comment.  Hat-tip:
    https://stackoverflow.com/questions/8283798/adding-a-comment-to-a-jpeg-file-using-python

    You might prefer writing comments to EXIF.  However, this idea is fast and
    safe (?).  Note: we don't put the comment *before* the EOF marker which is
    non-standard: e.g., ``rdjpgcom`` command-line tool cannot read.
    """
    s = generate_metadata_str(bundle_name, bundle_page)
    bs = s.encode()
    # start of comment
    b = b"\xff\xfe"
    # 2 bytes, unsigned int, little-endian
    b += struct.pack(">H", len(bs))
    # trailing null
    b += bs + b"\x00"
    with open(filename, "a+b") as f:
        f.write(b)


def processFileToBitmaps(
    file_name, dest, *, do_not_extract=False, debug_jpeg=False, add_metadata=True
):
    """Extract/convert each page of pdf into bitmap.

    We have various ways to do this, in rough order of preference:

    1. Extract a scanned bitmap "as-is"
    2. Render the page with PyMuPDF
    3. Render the page with Ghostscript

    The bitmaps will have some metadata written into them to prevent
    otherwise identical pages from producing images with identical
    hashes.  See Issue #1573.

    Args:
        file_name (str, Path): PDF file from which to extract bitmaps.
        dest (str, Path): where to save the resulting bitmap files.
            Must exist.

    Keyword Args:
        do_not_extract (bool): always render, do not extract even if
            it seems possible to do so.  This is off-by-default until
            we are confident extracting won't miss anything.
            See more detailed description in the user-facing command-line
            tool `plom-scan`.
        debug_jpeg (bool): make jpegs, randomly rotated of various
            quality settings, for debugging or demos.  Default: False.
        add_metadata (bool): add invisible metadata to each image
            including bundle name and random numbers.  Default: True.
            If you disable this, you can get two identical images
            (from different pages) giving identical hashes, which
            in theory is harmless but at least in 2022 was causing
            database/client issues.

    Returns:
        list: an list of the images of each page, ordered as in the input
        file.  Each entry is a `pathlib.Path`.

    Raises:
        RuntimeError: not a PDF and not something PyMuPDF can open.
        TypeError: not a PDF, but it can be opened by PyMuPDF.
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

    with fitz.open(file_name) as doc:
        if not doc.is_pdf:
            raise TypeError("This does not appear to be a PDF file")
        if doc.is_repaired:
            warn("PyMuPDF had to repair this PDF: perhaps it is damaged in some way?")

        files = []
        for p in doc:
            basename = f"{safeScan}-{(p.number + 1):05}"
            outname, msgs = try_to_extract_image(
                p,
                doc,
                dest,
                basename,
                file_name,
                do_not_extract=do_not_extract,
                add_metadata=add_metadata,
            )
            if outname is not None:
                files.append(outname)
                continue
            log.info(f"{basename}: Fitz render. No extract b/c: " + "; ".join(msgs))
            outname = render_page_to_bitmap(
                p,
                dest,
                basename,
                file_name,
                add_metadata=add_metadata,
            )
            # For testing, randomly make jpegs, rotated a bit, of various qualities
            if debug_jpeg and random.uniform(0, 1) <= 0.9:
                _ = make_mucked_up_jpeg(outname, dest / ("muck-" + basename + ".jpg"))
                outname.unlink()
                outname = _
            files.append(outname)
        assert len(files) == len(doc), "Expected one image per page"
    return files


def try_to_extract_image(
    p: fitz.Page,
    doc: fitz.Document,
    dest: Path,
    basename: str,
    bundle_name: str | Path,
    *,
    do_not_extract: bool = False,
    add_metadata: bool = True,
):
    """If possible/desirable, extract an image from a PDF page and save to disc.

    "Desirable" means there are no additional markings on the page; no
    information will be lost by looking only at the extracted image
    instead of the original page.

    Args:
        p: a page of a PDF document.
        doc: the document containing that page.  Yes it is indeed a
            bit strange to pass both the page and the document containing
            the page.  Bad things probably happen if you pass a page from
            a different document!
        dest: where to save the resulting bitmap file.
        basename: part of filename, used to influence the
            filename of the output.
        bundle_name: only used for metadata hackery
            uniqifying pages, you can pass whatever you want.

    Keyword Args:
        do_not_extract: always render, do no extract even if
            it seems possible to do so.  This is off-by-default until
            we are confident extracting won't miss anything.
            See more detailed description in the user-facing command-line
            tool `plom-scan`.
        add_metadata: add invisible metadata to each image
            including bundle name and random numbers.  Default: True.
            If you disable this, you can get two identical images
            (from different pages) giving identical hashes, which
            in theory is harmless but at least in 2022 was causing
            database/client issues.

    Returns:
        2-tuple: first entry is ``pathlib.Path`` or ``None``, where
        ``None`` means we could not (or chose not) to extract.
        Whereas a `Path` means we have extracted the image.
        The second return value is ``msgs`` a list of strings, which
        give semi-user-readable info about why we cannot/choose not
        to extract.
    """
    msgs = []
    # Any of these might indicate something more complicated than a scan
    # and hence we should be safe and just render the page.  We only try to
    # extract the bitmap under very conservative circumstances.  It is not
    # safe to assume that if there is a single image on the current page
    # then that is the scan - e.g., student annotates pdf using xournalpp and
    # then stamps a smiley-face `.png` there."
    if p.get_links():
        msgs.append("Has links")
    for _ in p.annots():
        msgs.append("Has annotations")
        break
    for _ in p.widgets():
        msgs.append("Has fillable forms")
        break
    # TODO: which is more expensive, this or getImageList?
    if p.get_text("text"):
        msgs.append("Has text")

    # TODO: Do later to get more info in prep for future change to default
    if do_not_extract:
        msgs.append("Disabled by flag")

    if msgs:
        return None, msgs

    r, d = extractImageFromFitzPage(p, doc)
    if not r:
        msgs.append(d)
        return None, msgs
    log.info(
        '%s: Extracted "%s" from single-image page %sx%s',
        basename,
        d["ext"],
        d["width"],
        d["height"],
    )
    if d["ext"].lower() not in PlomImageExts:
        # Issue #2346: could try to convert to png, but for now just let fitz render
        log.info(f"  {d['ext']} not in allowlist: leave for fitz render")
        msgs.append(f'extracted image is not {", ".join(PlomImageExts)}')
        return None, msgs
    outname = dest / (basename + "." + d["ext"])
    with open(outname, "wb") as f:
        f.write(d["image"])
    if add_metadata:
        # watermark for Issue #1573
        if d["ext"].lower() == "png":
            add_metadata_png(outname, bundle_name, p.number)
        elif d["ext"].lower() in ("jpeg", "jpg"):
            # We write some unique metadata into the JPEG file.  We could
            # use the EXIF data or a JPEG comment.  The latter seems safer
            # as we just append some bytes to the file...?  I'm concerned
            # about interactions with existing EXIF: for example `exif`
            # library cannot write longer "user_comment" field (see tests).
            add_metadata_jpeg_comment(outname, bundle_name, p.number)
            # add_metadata_jpeg_exif(outname, bundle_name, p.number)
        else:
            # there should be no other choice until PlomImageExts is updated
            raise ValueError(f"No support for watermarking \"{d['ext']}\" files")
    return outname, msgs


def render_page_to_bitmap(
    p: fitz.Page,
    dest: Path,
    basename: str,
    bundle_name: str | Path,
    *,
    add_metadata: bool = True,
) -> Path:
    """Use PyMuPDF to render a PDF page to an image.

    Args:
        p: a page of a PDF document.
        dest: where (directory) to save the resulting
            bitmap file.
        basename: part of filename, used to influence the
            filename of the output.
        bundle_name: the name and/or path of the bundle, only used for
            metadata hackery to uniqify page images: you can pass
            whatever you want.

    Keyword Args:
        add_metadata: add invisible metadata to each image
            including bundle name and random numbers.  Default: True.
            If you disable this, you can get two identical images
            (from different pages) giving identical hashes, which
            in theory is harmless but at least in 2022 was causing
            database/client issues.

    Returns:
        pathlib.Path: the rendered image on disc.

    Raises:
        ValueError: overly weird shapes such as too tall ("Safeway receipt")
            or two wide ("fortune cookie").
    """
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
    # would display such a thin wide strip at too large a scale.
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
    # # For testing, choose widely varying random sizes
    # z = random.uniform(1, 5)
    log.info(f"{basename}: Fitz render z={z:4.2f}.")
    pix = p.get_pixmap(matrix=fitz.Matrix(z, z), annots=True)
    # TODO: sometimes width and height get mixed up: Issues #1148, #1935
    # but one of them should match the target, without worrying which is which
    if not (pix.width in (W, H) or pix.height in (W, H)):
        _m = (
            f"Debug: {p}: some kind of rounding error in scaling image?"
            f" Rendered to {pix.width}x{pix.height} from target {W}x{H}"
        )
        warn(_m)
        log.warning(_m)

    pngname = dest / (basename + ".png")
    jpgname = dest / (basename + ".jpg")
    if add_metadata:
        # We write some unique metadata into the PNG file to avoid Issue #1573
        metadata = generate_png_metadata(bundle_name, p.number)
        pix.pil_save(pngname, optimize=True, pnginfo=metadata)
    else:
        # pil_save 10% smaller but 2x-3x slower, Issue #1866
        pix.save(pngname)

    exy = PIL.Image.Exif()  # empty exif data
    if add_metadata:
        # We write some unique metadata into the JPEG exif data to avoid Issue #1573
        assert PIL.ExifTags.TAGS[37510] == "UserComment"
        exy[37510] = generate_metadata_str(bundle_name, p.number)
    # TODO: add progressive=True?
    # Note subsampling off to avoid mucking with red hairlines
    pix.pil_save(jpgname, quality=90, optimize=True, subsampling=0, exif=exy)

    # Keep the jpeg if its at least a little smaller
    if jpgname.stat().st_size < 0.9 * pngname.stat().st_size:
        pngname.unlink()
        return jpgname
    jpgname.unlink()
    return pngname
    # WebP here is also an option, Issue #1864.


def make_mucked_up_jpeg(f: Path, outname: Path) -> Path:
    """Given an input file, do horrid things to it in the name of debugging.

    Args:
        f: input
        outname: output file to be created.

    Returns:
        The output file again.
    """
    img = pil_load_with_jpeg_exif_rot_applied(f)

    angle = random.choice([90.5, 180.4, -90.3, -88, -1])
    msgs = [f"hard-rotate {angle}"]
    try:
        bilinear = PIL.Image.Resampling.BILINEAR
    except AttributeError:
        # Remove this workaround once minimum Pillow is 9.1.x
        # pylint: disable=no-member
        bilinear = PIL.Image.BILINEAR  # type: ignore
    img = img.rotate(
        angle,
        resample=bilinear,
        expand=True,
        fillcolor=(128, 128, 128, 0),
    )
    quality = random.choice([6, 30, 94, 94, 94])
    msgs.append(f"quality {quality}")
    r = random.choice([None, None, None, 3, 6, 8])
    if r:
        msgs.append(f"exif rotate {r}")
    log.info("  Randomly making jpeg " + ", ".join(msgs))
    img.save(outname, "JPEG", quality=quality, optimize=True)
    im_shell = exif.Image(outname)
    # debugging so maybe we don't need unique JPEG exif metadata for Issue #1573
    # im_shell.set("user_comment", generate_metadata_str(bundle_name, p.number))
    if r:
        im_shell.set("orientation", r)
    # TODO: MyPy seems concerned with these lines
    with open(outname, "wb") as f:  # type: ignore
        f.write(im_shell.get_file())  # type: ignore
    # add_metadata_jpeg_comment(outname, file_name, p.number)
    return outname


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
    """Convert each page of pdf into png using ghostscript."""
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
    """Apply a simple gamma shift to an image."""
    subprocess.run(
        ["mogrify", "-quiet", "-gamma", "0.5", fn],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


def postProcessing(thedir, dest, skip_gamma: bool = False) -> None:
    """Do post processing on a directory of scanned bitmaps.

    Args:
        thedir (str, Path): a directory full of bitmaps.
        dest (str, Path): move images here (???).
        skip_gamma: skip the white balancing.

    Returns:
        None
    """
    thedir = Path(thedir)
    dest = Path(dest)

    if not skip_gamma:
        # TODO: maybe tiff as well?  Not jpeg: not anything lossy!
        print("Gamma shift the PNG images")
        # list and len bit crude here: more pythonic to leave as iterator?
        stuff = list(thedir.glob("*.png"))
        N = len(stuff)
        with Pool() as p:
            _ = list(tqdm(p.imap_unordered(gamma_adjust, stuff), total=N))
        # Pool does this loop, but in parallel
        # for x in glob.glob("..."):
        #     gamma_adjust(x)

    fileList = []
    for ext in PlomImageExts:
        fileList.extend(thedir.glob(f"*.{ext}"))
    # move them to pageimages for barcode reading
    for file in fileList:
        shutil.move(file, dest / file.name)


def process_scans(
    pdf_fname, bundle_dir, skip_gamma=False, skip_img_extract=False, *, demo=False
):
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

    Keyword Args:
        demo (bool): Simulate scanning with random rotations, adding
            noise, lower-quality jpegs, etc.  Default: False

    Returns:
        list: filenames (`pathlib.Path`) in page order, one for each page.
        The same files will be in the directory specified by `bundle_dir`.
        We do not add any other files to that directory.
    """
    make_bundle_dir(bundle_dir)
    bitmaps_dir = bundle_dir / "scanPNGs"
    files = processFileToBitmaps(
        pdf_fname,
        bitmaps_dir,
        do_not_extract=skip_img_extract,
        debug_jpeg=demo,
    )
    # TODO: if not skip_gamma, this might clear our image uniqifier (#1573)
    postProcessing(bitmaps_dir, bundle_dir / "pageImages", skip_gamma)
    #           ,,,
    #          (o o)
    # -----ooO--(_)--Ooo------
    # hacky myhacker was here!
    # (instead we could rethink postProcessing)
    files = [bundle_dir / "pageImages" / f.name for f in files]
    return files
