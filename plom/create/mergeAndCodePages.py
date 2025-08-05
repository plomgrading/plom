# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from __future__ import annotations

import math
import pathlib
import tempfile
from pathlib import Path
from typing import Any

# import pyqrcode
import pymupdf
import segno

from plom.create import paperdir
from plom.spec_verifier import (
    build_page_to_group_name_dict,
    build_page_to_version_dict,
    get_question_labels,
)
from plom.tpv_utils import encodeScrapPaperCode, encodeTPV

# from plom.misc_utils import run_length_encoding


def create_QR_codes(
    papernum: int, pagenum: int, ver: int, code: str, dur: pathlib.Path
) -> list[pathlib.Path]:
    """Creates QR codes as png files and a dictionary of their filenames.

    Arguments:
        papernum: the paper number.
        pagenum: the page number.
        ver: the version of this page.
        code: short digit code distinguishing this document from others.
        dur: a directory to save the QR codes.

    Returns:
        List of ``pathlib.Path` for PNG files for each corner's QR code.
        The corners are indexed counterclockwise from the top-right:

            index | meaning
            ------|--------
            0     | top-right
            1     | top-left
            2     | bottom-left
            3     | bottom-right
    """
    qr_file = []
    for corner_index in range(4):
        # Note: TPV indexes corners from 1
        tpv = encodeTPV(papernum, pagenum, ver, corner_index + 1, code)
        filename = dur / f"qr_{papernum:04}_pg{pagenum}_{corner_index + 1}.png"

        # qr_code = pyqrcode.create(tpv, error="H")
        # qr_code.png(filename, scale=4)

        qr_code = segno.make(tpv, error="H")
        # MyPy complains about pathlib.Path here but it works
        qr_code.save(filename, scale=4)  # type: ignore[arg-type]

        qr_file.append(filename)

    return qr_file


def label_for_top_of_page(paper: str | int, group: str, page: int) -> str:
    """Format the text label that appears at the top of each page.

    If paper is a string, show it as-is, else zero-pad to 4 digits.
    """
    if not isinstance(paper, str):
        paper = f"{paper:04}"
    return f"Paper {paper}  {group}  p. {page}"


def _create_QRcoded_pdf(
    spec: dict[str, Any],
    papernum: int,
    qvmap_row: dict[int | str, int],
    tmpdir: pathlib.Path,
    source_versions: dict[int, pathlib.Path],
    *,
    no_qr: bool = False,
    paperstr: str | None = None,
) -> pymupdf.Document:
    """Creates a PDF document from versioned sources, stamps QR codes on the corners.

    (We create 4 QR codes but only add 3 of them because of the staple side, see below).

    Arguments:
        spec (dict): A validated assessment specification
        papernum (int): the paper number.
        qvmap_row: version number for each question of this paper.
            and optionally the id page.  A row of the "qvmap".
        tmpdir (pathlib.Path): a place where we can make temporary files.
        source_versions: dict of paths for the source versions, keyed
            by version.  Some can be missing as long as they don't appear
            in the ``qvmap_row``.

    Keyword Arguments:
        no_qr (bool): whether to paste in QR-codes (default: False)
            Note backward logic: False means yes to QR-codes.
        paperstr: override the default string version of the paper number.

    Returns:
        PDF document, apparently open, which seems to me a scary
        thing to be handing around.  Caller is responsible for closing it.

    Raises:
        RuntimeError: one or more of your version<N>.pdf files not found.
    """
    # from spec get the mapping from page to group
    page_to_group_name = build_page_to_group_name_dict(spec)
    # also build page to version mapping from spec and the question-version dict
    page_to_version = build_page_to_version_dict(spec, qvmap_row)

    # dict of version (int) -> source pdf (pymupdf.Document)
    pdf_version = {v: pymupdf.open(f) for v, f in source_versions.items()}

    exam = pymupdf.open()
    # Insert the relevant page-versions into this pdf.
    for page_index in range(1, spec["numberOfPages"] + 1):
        # Pymupdf starts pagecounts from 0 rather than 1. So offset things.
        exam.insert_pdf(
            pdf_version[page_to_version[page_index]],
            from_page=page_index - 1,
            to_page=page_index - 1,
            start_at=-1,
        )

    # The above loops over pages: a lot of "churn"; large font tables [1], etc.
    # Instead, do a run-length encoding of the page version then copy multiple
    # pages at a time.  In single-version case, we do a single block of copying.
    # [1] https://gitlab.com/plom/plom/-/issues/1795
    # ver_runs = run_length_encoding([v for p, v in page_to_version.items()])
    # for run in ver_runs:
    #     ver, start, end = run
    #     exam.insert_pdf(
    #         pdf_version[ver],
    #         from_page=start,
    #         to_page=end - 1,
    #         start_at=-1,
    #     )

    for p in range(1, spec["numberOfPages"] + 1):
        odd: bool | None = (p - 1) % 2 == 0
        if no_qr:
            odd = None
            qr_files = []
        else:
            ver = page_to_version[p]
            qr_files = create_QR_codes(papernum, p, ver, spec["publicCode"], tmpdir)

        label = label_for_top_of_page(
            papernum if paperstr is None else paperstr,
            page_to_group_name[p],
            p,
        )
        pdf_page_add_labels_QRs(exam[p - 1], spec["name"], label, qr_files, odd=odd)

    for ver, pdf in pdf_version.items():
        pdf.close()
    return exam


def pdf_page_add_stamp(page: pymupdf.Page, stamp: str) -> None:
    """Add top-middle stamp to a PDF page.

    Args:
        page: a particular page of a PDF file.
        stamp: text for the top-middle

    Returns:
        None, but modifies page as a side-effect.
    """
    w = 70  # box width
    mx, my = (15, 20)  # margins

    pg_width = page.bound().width

    tw = pymupdf.TextWriter(page.rect)
    maxbox = pymupdf.Rect(mx + w + 10, my, pg_width - mx - w - 10, my + 30)
    # page.draw_rect(maxbox, color=(1, 0, 0))
    excess = tw.fill_textbox(
        maxbox,
        stamp,
        align=pymupdf.TEXT_ALIGN_CENTER,
        fontsize=14,
        font=pymupdf.Font("helv"),
    )
    assert not excess, "Text didn't fit: is paper number label too long?"
    r = tw.text_rect
    # stems of p, q mean a bit less added in y
    r = r + (-4, -4, 4, 2)
    page.draw_rect(r, color=(0, 0, 0), width=0.5)
    tw.write_text(page)


def pdf_page_add_labels_QRs(
    page: pymupdf.Page,
    shortname: str,
    stamp: str,
    qr_code: list[pathlib.Path],
    odd: bool | None = True,
) -> None:
    """Add top-middle stamp, QR codes and staple indicator to a PDF page.

    Args:
        page: a particular page of an open PDF file.  We will modify it.
        shortname: a short string that we will write on the staple
            indicator.
        stamp: text for the top-middle
        qr_code: QR images, if empty, don't do corner work.
        odd: True for an odd page number (counting from 1),
            False for an even page, and None if you don't want to draw a
            staple corner.

    Returns:
        None: but modifies page as a side-effect.
    """
    w = 70  # box width
    mx, my = (15, 20)  # margins

    pg_width = page.bound().width
    pg_height = page.bound().height

    # create two "do not write" (DNW) rectangles accordingly with TL (top left) and TR (top right)
    rDNW_TL = pymupdf.Rect(mx, my, mx + w, my + w)
    rDNW_TR = pymupdf.Rect(pg_width - mx - w, my, pg_width - mx, my + w)

    # page-corner boxes for the QR codes
    # TL: Top Left, TR: Top Right, BL: Bottom Left, BR: Bottom Right
    TL = pymupdf.Rect(mx, my, mx + w, my + w)
    TR = pymupdf.Rect(pg_width - w - mx, my, pg_width - mx, my + w)
    BL = pymupdf.Rect(mx, pg_height - my - w, mx + w, pg_height - my)
    BR = pymupdf.Rect(
        pg_width - mx - w, pg_height - my - w, pg_width - mx, pg_height - my
    )

    pdf_page_add_stamp(page, stamp)

    # special code to skip staple mark and QR codes
    if odd is None:
        return

    # stamp DNW near staple: even/odd pages different
    # Top Left for odd pages (1 is 1st), Top Right for even
    rDNW = rDNW_TL if odd else rDNW_TR
    shape = page.new_shape()
    shape.draw_line(rDNW.top_left, rDNW.top_right)
    if odd:
        shape.draw_line(rDNW.top_right, rDNW.bottom_left)
    else:
        shape.draw_line(rDNW.top_right, rDNW.bottom_right)
    shape.finish(width=0.5, color=(0, 0, 0), fill=(0.75, 0.75, 0.75))
    shape.commit()

    pivot = (rDNW.tl + rDNW.br) / 2
    r = pymupdf.Rect(rDNW.tl.x - 30, pivot.y - 12, rDNW.tr.x + 30, pivot.y + 12)
    tw = pymupdf.TextWriter(page.rect)
    excess = tw.fill_textbox(r, shortname, fontsize=8, align=pymupdf.TEXT_ALIGN_CENTER)
    assert not excess, "Text didn't fit: is shortname too long?"

    mat = pymupdf.Matrix(45 if odd else -45)
    tw.write_text(page, color=(0, 0, 0), morph=(pivot, mat))
    # page.draw_rect(r, color=(1, 0, 0))

    if not qr_code:
        # no more processing of this page if QR codes unwanted
        return

    # paste in the QR-codes
    # Remember that we only add 3 of the 4 QR codes for each page since
    # we always have a corner section for staples and such
    # Note: draw png first so it doesn't occlude the outline
    if odd:
        page.insert_image(TR, pixmap=pymupdf.Pixmap(qr_code[0]), overlay=True)
        page.draw_rect(TR, color=[0, 0, 0], width=0.5)
    else:
        page.insert_image(TL, pixmap=pymupdf.Pixmap(qr_code[1]), overlay=True)
        page.draw_rect(TL, color=[0, 0, 0], width=0.5)
    page.insert_image(BL, pixmap=pymupdf.Pixmap(qr_code[2]), overlay=True)
    page.insert_image(BR, pixmap=pymupdf.Pixmap(qr_code[3]), overlay=True)
    page.draw_rect(BL, color=[0, 0, 0], width=0.5)
    page.draw_rect(BR, color=[0, 0, 0], width=0.5)


def pdf_page_add_name_id_box(
    page: pymupdf.Page,
    name: str,
    sid: str,
    x: float | None = None,
    y: float | None = None,
    *,
    signherebox: bool = True,
) -> None:
    """Creates the extra info (usually student name and id) boxes and places them in the first page.

    Arguments:
        page: Page of a PDF document, will be modified as a side effect.
        name: student name.
        sid: student id.
        x: specifies the x-coordinate where the id and name
            will be placed, as a float from 0 to 100, where 0 has the centre
            of the box at left of the page and 100 has the centre at the right
            of the page.  If None, defaults to 50.  Note that unlike the
            y value, small and large values of can overhang the edge of the
            page: this is intentional as centring the centre of this
            box on the centre of the template works best if a name is
            unexpectedly long.
        y: specifies the y-coordinate where the id and name
            will be placed, as a float from 0 to 100, where 0 is the top
            and 100 is the bottom of the page.  If None, defaults to 42
            for historical reasons (to match the position in our demo).

    Keyword Arguments:
        signherebox: add a "sign here" box, default True.

    Raises:
        ValueError: Raise error if the student name and number is not encodable.

    Returns:
        None: modifies the first input as a side effect.
    """
    if x is None:
        x = 50
    if y is None:
        y = 42

    page_width = page.bound().width
    page_height = page.bound().height

    sign_here = "Please sign here"

    box_width = 410
    box1_height = 108  # two lines of 36 pt and 1.5 baseline
    box2_height = 90

    name_id_rect = pymupdf.Rect(
        page_width * (x / 100.0) - box_width / 2,
        (page_height - box1_height - box2_height) * (y / 100.0),
        page_width * (x / 100.0) + box_width / 2,
        (page_height - box1_height - box2_height) * (y / 100.0) + box1_height,
    )
    signature_rect = pymupdf.Rect(
        name_id_rect.x0,
        name_id_rect.y1,
        name_id_rect.x1,
        name_id_rect.y1 + box2_height,
    )
    page.draw_rect(name_id_rect, color=(0, 0, 0), fill=(1, 1, 1), width=3)
    if signherebox:
        page.draw_rect(signature_rect, color=(0, 0, 0), fill=(1, 1, 1), width=3)

    # first place the name with adaptive fontsize
    fontsize = 37
    w = math.inf
    font = pymupdf.Font("helv")
    while w > name_id_rect.width:
        if fontsize < 6:
            raise RuntimeError(
                f'Overly long name? fontsize={fontsize} for name="{name}"'
            )
        fontsize -= 1
        w = font.text_length(name, fontsize=fontsize)
    tw = pymupdf.TextWriter(page.rect)
    tw.append(
        pymupdf.Point(page_width * (x / 100.0) - w / 2, name_id_rect.y0 + 38),
        name,
        fontsize=fontsize,
    )

    # then place the student number
    fontsize = 36
    w = font.text_length(sid, fontsize=fontsize)
    tw.append(
        pymupdf.Point(page_width * (x / 100.0) - w / 2, name_id_rect.y0 + 90),
        sid,
        fontsize=fontsize,
    )
    tw.write_text(page)

    # and finally the "sign here" watermark
    if not signherebox:
        return
    fontsize = 48
    w = font.text_length(sign_here, fontsize=fontsize)
    tw = pymupdf.TextWriter(page.rect, color=(0.9, 0.9, 0.9))
    tw.append(
        pymupdf.Point(page_width * (x / 100.0) - w / 2, signature_rect.y0 + 52),
        sign_here,
        fontsize=fontsize,
    )
    tw.write_text(page)


def make_PDF(
    spec,
    papernum: int,
    question_versions: dict[int | str, int],
    extra: dict[str, Any] | None = None,
    xcoord: float | None = None,
    ycoord: float | None = None,
    no_qr: bool = False,
    fakepdf: bool = False,
    *,
    where: Path | None = None,
    source_versions_path: Path | str | None = None,
    source_versions: dict[int, Path] | None = None,
    font_subsetting: bool | None = None,
    paperstr: str | None = None,
) -> pathlib.Path | None:
    """Make a PDF of particular versions, with QR codes, and optionally name stamped.

    Take pages from each source (using `questions_versions`/`page_versions`) and
    add QR codes and "DNW" staple-corner indicators.  Optionally stamp the
    student name/id from `extra` onto the cover page.  Save the new PDF
    file into the `paperdir` (typically "papersToPrint").

    Arguments:
        spec (dict | SpecVerifier): A validated specification
        papernum: the paper number.
        question_versions: the version of each question for this paper.
            Note this is an input and must be predetermined before
            calling.
        extra: Dictionary with student id and name or None
            to default not printing any prename.
        xcoord: horizontal positioning of the prename box, or a default
            if None or omitted.
        ycoord: vertical positioning of the prename box, or a default
            if None or omitted.
        no_qr (bool): determine whether or not to paste in qr-codes.
            Somewhat deprecated, definitely use it as kwarg if you're
            writing new code.
        fakepdf (bool): when true, the build empty "pdf" files by just
            touching fhe files.  This is could be used in testing or to
            save time when we have no use for the actual files.  Why?
            Maybe later confirmation steps check these files exist or
            something like that...
            Somewhat deprecated, definitely use it as kwarg if you're
            writing new code.

    Keyword Args:
        where: where to save the files, with some default if omitted.
        source_versions: ordered list of locations of the source-version
            files.  Mutually-exclusive with ``source_versions_path``.
        source_versions_path: location of the source versions directory.
            Defaults to "./sourceVersions" if this and ``source_versions``
            are omitted.
        font_subsetting: if None/omitted, do a generally-sensible default
            of using subsetting only when *we* added non-ascii characters.
            True forces subsetting and False disables it.
            We embed fonts for names and other overlay.  But if there are
            non-Latin characters (e.g., CJK) in names, then the embedded
            font is quite large (several megabytes).
            Note: in theory, subsetting could muck around with fonts from
            the source (i.e., if they were NOT previously subsetted).
            So we only do the subsetting if we're added non-ascii chars
            in any of the shortname, student name or question labels.
            Non-ascii is a stronger requirement than needed,
        paperstr: override the default string version of the paper number.
            Probably you don't need to do this, although Mocker does.

    Returns:
        pathlib.Path: the file that was just written, or None in the slightly
        strange, perhaps deprecated ``fakepdf`` case.

    Raises:
        ValueError: Raise error if the student name and number is not encodable
    """
    if where is None:
        where = paperdir
    if extra:
        save_name = where / f"exam_{papernum:04}_{extra['id']}.pdf"
    else:
        save_name = where / f"exam_{papernum:04}.pdf"

    # make empty files instead of PDFs
    if fakepdf:
        save_name.touch()
        return None

    if source_versions is not None:
        assert (
            source_versions_path is None
        ), "cannot specify both source_versions and source_versions_path"
    else:
        if source_versions_path:
            _src = Path(source_versions_path)
        else:
            _src = Path("sourceVersions")
        source_versions = {
            v: _src / f"version{v}.pdf" for v in range(1, spec["numberOfVersions"] + 1)
        }

    # Build all relevant pngs in a temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        exam = _create_QRcoded_pdf(
            spec,
            papernum,
            question_versions,
            Path(tmp_dir),
            source_versions,
            no_qr=no_qr,
            paperstr=paperstr,
        )

    # If provided with student name and id, preprint on cover
    if extra:
        pdf_page_add_name_id_box(exam[0], extra["name"], extra["id"], xcoord, ycoord)

    do_subset = False
    if extra and not extra["name"].isascii():
        do_subset = True
    if not spec["name"].isascii():
        do_subset = True
    for label in get_question_labels(spec):
        if not label.isascii():
            do_subset = True

    if font_subsetting is None:
        font_subsetting = do_subset
    if font_subsetting:
        exam.subset_fonts()

    # Add the deflate option to compress the embedded pngs
    # see https://pymupdf.readthedocs.io/en/latest/document/#Document.save
    # also do garbage collection to remove duplications within pdf
    # and try to clean up as much as possible.
    # `linear=True` causes https://gitlab.com/plom/plom/issues/284

    # Also worth noting that this will automatically overwrite any files
    # in the same directory that have the same name.
    exam.save(save_name, garbage=4, deflate=True, clean=True)
    exam.close()

    return save_name


def create_invalid_QR_and_bar_codes(dur: pathlib.Path) -> list[pathlib.Path]:
    """Creates qr-codes and barcodes to make sure we handle invalid codes, for testing.

    More precisely, it creates 4 png images.
        * an invalid plom qr-code (read by plom)
        * an EAN-13 barcode (plom ignores)
        * a Code128 barcode (plom ignores)
        * a valid micro-qr scrap-paper code for the top-left corner of a page

    Arguments:
        dur: a directory to save the QR codes.

    Returns:
        List of ``pathlib.Path` for PNG files, the qr-code then the barcodes.
    """
    qr_files = []
    filename = dur / "qr_invalid.png"
    # make a qr-code using segno
    qr_code = segno.make("not even wrong", error="H")
    qr_code.save(filename, scale=4)  # type: ignore[arg-type]
    qr_files.append(filename)

    # a barcode using zxing-cpp
    # see https://github.com/zxing-cpp/zxing-cpp/blob/master/wrappers/python/demo_writer.py
    import zxingcpp
    from PIL import Image

    # make an EAN-13
    filename = dur / "ean_invalid.png"
    img = zxingcpp.write_barcode(
        zxingcpp.BarcodeFormat.EAN13, "0123456789012", width=300, height=100
    )
    Image.fromarray(img).save(filename)
    qr_files.append(filename)
    # make a CODE128
    filename = dur / "code_invalid.png"
    img = zxingcpp.write_barcode(
        zxingcpp.BarcodeFormat.Code128, "even more wrong", width=300, height=100
    )
    Image.fromarray(img).save(filename)
    qr_files.append(filename)
    # make a top-left scrap-paper micro qr code
    filename = dur / "valid_tl_scrap_code.png"
    qr = segno.make_micro(encodeScrapPaperCode(1))
    # MyPy complains about pathlib.Path here but it works
    qr.save(filename, border=2, scale=4)  # type: ignore[arg-type]
    qr_files.append(filename)

    return qr_files
