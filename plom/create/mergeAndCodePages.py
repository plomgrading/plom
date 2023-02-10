# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee

import tempfile
import math
from pathlib import Path

# import pyqrcode
import segno
import fitz

from plom.create import paperdir
from plom.specVerifier import build_page_to_group_dict, build_page_to_version_dict
from plom.tpv_utils import encodeTPV


# from plom.misc_utils import run_length_encoding


def create_QR_codes(papernum, pagenum, ver, code, dur):
    """Creates QR codes as png files and a dictionary of their filenames.

    Arguments:
        papernum (int): the paper/test number.
        pagenum (int): the page number.
        ver (int): the version of this page.
        code (str): 6 digits distinguishing this document from others.
        dur (pathlib.Path): a directory to save the QR codes.

    Returns:
        list: of ``pathlib.Path` for PNG files for each corner's QR code.
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
        qr_code.save(filename, scale=4)

        qr_file.append(filename)

    return qr_file


def create_exam_and_insert_QR(
    spec,
    papernum,
    question_versions,
    tmpdir,
    *,
    no_qr=False,
):
    """Creates the exam objects and insert the QR codes.

    Creates the exams objects from the pdfs stored at sourceVersions.
    Then adds the 3 QR codes for each page.
    (We create 4 QR codes but only add 3 of them because of the staple side, see below).

    Arguments:
        spec (dict): A validated test specification
        papernum (int): the paper/test number.
        question_versions (dict): version number for each question of this paper.
        tmpdir (pathlib.Path): a place where we can make temporary files.

    Keyword Arguments:
        no_qr (bool): whether to paste in QR-codes (default: False)
            Note backward logic: False means yes to QR-codes.

    Returns:
        fitz.Document: PDF document.

    Raises:
        RuntimeError: one or more of your versionN.pdf files not found.
    """
    # from spec get the mapping from page to group
    page_to_group = build_page_to_group_dict(spec)
    # also build page to version mapping from spec and the question-version dict
    page_to_version = build_page_to_version_dict(spec, question_versions)

    source = Path("sourceVersions")
    # dict of version (int) -> source pdf (fitz.Document)
    pdf_version = {}
    for ver in range(1, spec["numberOfVersions"] + 1):
        pdf_version[ver] = fitz.open(source / f"version{ver}.pdf")

    exam = fitz.open()
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
        # Workaround Issue #1347: unnecessary for pymupdf>=1.18.7
        exam[p - 1].clean_contents()
        # name of the group to which page belongs
        group = page_to_group[p]
        text = f"Test {papernum:04} {group:5} p. {p}"
        odd = (p - 1) % 2 == 0
        if no_qr:
            odd = None
            qr_files = {}
        else:
            ver = page_to_version[p]
            qr_files = create_QR_codes(papernum, p, ver, spec["publicCode"], tmpdir)

        pdf_page_add_labels_QRs(exam[p - 1], spec["name"], text, qr_files, odd=odd)

    for ver, pdf in pdf_version.items():
        pdf.close()
    return exam


def pdf_page_add_stamp(page, stamp):
    """Add top-middle stamp to a PDF page.

    args:
        page (fitz.Page): a particular page of a PDF file.
        stamp (str): text for the top-middle

    returns:
        None: but modifies page as a side-effect.
    """
    w = 70  # box width
    mx, my = (15, 20)  # margins

    pg_width = page.bound().width

    tw = fitz.TextWriter(page.rect)
    maxbox = fitz.Rect(mx + w + 10, my, pg_width - mx - w - 10, my + 30)
    # page.draw_rect(maxbox, color=(1, 0, 0))
    excess = tw.fill_textbox(
        maxbox, stamp, align=fitz.TEXT_ALIGN_CENTER, fontsize=14, font=fitz.Font("helv")
    )
    assert not excess, "Text didn't fit: is paper number label too long?"
    r = tw.text_rect
    r = fitz.Rect(
        pg_width // 2 - r.width / 2, my, pg_width // 2 + r.width / 2, my + r.height
    )
    page.draw_rect(r, color=(0, 0, 0), width=0.5)
    tw.write_text(page)


def pdf_page_add_labels_QRs(page, shortname, stamp, qr_code, odd=True):
    """Add top-middle stamp, QR codes and staple indicator to a PDF page.

    args:
        page (fitz.Page): a particular page of a PDF file.
        shortname (str): a short string that we will write on the staple
            indicator.
        stamp (str): text for the top-middle
        qr_code (dict): QR images, if empty, don't do corner work.
        odd (bool/None): True for an odd page number (counting from 1),
            False for an even page, and None if you don't want to draw a
            staple corner.

    returns:
        None: but modifies page as a side-effect.
    """
    w = 70  # box width
    mx, my = (15, 20)  # margins

    pg_width = page.bound().width
    pg_height = page.bound().height

    # create two "do not write" (DNW) rectangles accordingly with TL (top left) and TR (top right)
    rDNW_TL = fitz.Rect(mx, my, mx + w, my + w)
    rDNW_TR = fitz.Rect(pg_width - mx - w, my, pg_width - mx, my + w)

    # page-corner boxes for the QR codes
    # TL: Top Left, TR: Top Right, BL: Bottom Left, BR: Bottom Right
    TL = fitz.Rect(mx, my, mx + w, my + w)
    TR = fitz.Rect(pg_width - w - mx, my, pg_width - mx, my + w)
    BL = fitz.Rect(mx, pg_height - my - w, mx + w, pg_height - my)
    BR = fitz.Rect(pg_width - mx - w, pg_height - my - w, pg_width - mx, pg_height - my)

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
    r = fitz.Rect(rDNW.tl.x - 30, pivot.y - 12, rDNW.tr.x + 30, pivot.y + 12)
    tw = fitz.TextWriter(page.rect)
    excess = tw.fill_textbox(r, shortname, fontsize=8, align=fitz.TEXT_ALIGN_CENTER)
    assert not excess, "Text didn't fit: is shortname too long?"

    mat = fitz.Matrix(45 if odd else -45)
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
        page.insert_image(TR, pixmap=fitz.Pixmap(qr_code[0]), overlay=True)
        page.draw_rect(TR, color=[0, 0, 0], width=0.5)
    else:
        page.insert_image(TL, pixmap=fitz.Pixmap(qr_code[1]), overlay=True)
        page.draw_rect(TL, color=[0, 0, 0], width=0.5)
    page.insert_image(BL, pixmap=fitz.Pixmap(qr_code[2]), overlay=True)
    page.insert_image(BR, pixmap=fitz.Pixmap(qr_code[3]), overlay=True)
    page.draw_rect(BL, color=[0, 0, 0], width=0.5)
    page.draw_rect(BR, color=[0, 0, 0], width=0.5)


def pdf_page_add_name_id_box(page, name, sid, x=None, y=None, signherebox=True):
    """Creates the extra info (usually student name and id) boxes and places them in the first page.

    Arguments:
        page (fitz.Page): Page of a PDF document, will be modified as a side
            effect.
        name (str): student name.
        sid (str): student id.
        x (float): specifies the x-coordinate where the id and name
            will be placed, as a float from 0 to 100, where 0 has the centre
            of the box at left of the page and 100 has the centre at the right
            of the page.  If None, defaults to 50.  Note that unlike the
            y value, small and large values of can overhang the edge of the
            page: this is intentional as centring the centre of this
            box on the centre of the template works best if a name is
            unexpectedly long.
        y (float): specifies the y-coordinate where the id and name
            will be placed, as a float from 0 to 100, where 0 is the top
            and 100 is the bottom of the page.  If None, defaults to 42
            for historical reasons (to match the position in our demo).

    Keyword args:
        signherebox (bool): add a "sign here" box, default True.

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

    name_id_rect = fitz.Rect(
        page_width * (x / 100.0) - box_width / 2,
        (page_height - box1_height - box2_height) * (y / 100.0),
        page_width * (x / 100.0) + box_width / 2,
        (page_height - box1_height - box2_height) * (y / 100.0) + box1_height,
    )
    signature_rect = fitz.Rect(
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
    font = fitz.Font("helv")
    while w > name_id_rect.width:
        if fontsize < 6:
            raise RuntimeError(
                f'Overly long name? fontsize={fontsize} for name="{name}"'
            )
        fontsize -= 1
        w = font.text_length(name, fontsize=fontsize)
    tw = fitz.TextWriter(page.rect)
    tw.append(
        fitz.Point(page_width / 2 - w / 2, name_id_rect.y0 + 38),
        name,
        fontsize=fontsize,
    )

    # then place the student number
    fontsize = 36
    w = font.text_length(sid, fontsize=fontsize)
    tw.append(
        fitz.Point(page_width / 2 - w / 2, name_id_rect.y0 + 90),
        sid,
        fontsize=fontsize,
    )
    tw.write_text(page)

    # and finally the "sign here" watermark
    if not signherebox:
        return
    fontsize = 48
    w = font.text_length(sign_here, fontsize=fontsize)
    tw = fitz.TextWriter(page.rect, color=(0.9, 0.9, 0.9))
    tw.append(
        fitz.Point(page_width / 2 - w / 2, signature_rect.y0 + 52),
        sign_here,
        fontsize=fontsize,
    )
    tw.write_text(page)


def make_PDF(
    spec,
    papernum,
    question_versions,
    extra=None,
    no_qr=False,
    fakepdf=False,
    xcoord=None,
    ycoord=None,
):
    """Make a PDF of particular versions, with QR codes, and optionally name stamped.

    Take pages from each source (using `questions_versions`/`page_versions`) and
    add QR codes and "DNW" staple-corner indicators.  Optionally stamp the
    student name/id from `extra` onto the cover page.  Save the new PDF
    file into the `paperdir` (typically "papersToPrint").

    Arguments:
        spec (dict): A validated test specification
        papernum (int): the paper/test number.
        question_versions (dict): the version of each question for this paper.
            Note this is an input and must be predetermined before
            calling.
        extra (dict/None): Dictionary with student id and name or None.
        no_qr (bool): determine whether or not to paste in qr-codes.
        fakepdf (bool): when true, the build empty "pdf" files by just
            touching fhe files.  This is could be used in testing or to
            save time when we have no use for the actual files.  Why?
            Maybe later confirmation steps check these files exist or
            something like that...
        xcoord (float): horizontal positioning of the prename box.
        ycoord (float): vertical positioning of the prename box.

    Raises:
        ValueError: Raise error if the student name and number is not encodable
    """
    if extra:
        save_name = paperdir / f"exam_{papernum:04}_{extra['id']}.pdf"
    else:
        save_name = paperdir / f"exam_{papernum:04}.pdf"

    # make empty files instead of PDFs
    if fakepdf:
        save_name.touch()
        return

    # Build all relevant pngs in a temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        exam = create_exam_and_insert_QR(
            spec,
            papernum,
            question_versions,
            Path(tmp_dir),
            no_qr=no_qr,
        )

    # If provided with student name and id, preprint on cover
    if extra:
        pdf_page_add_name_id_box(exam[0], extra["name"], extra["id"], xcoord, ycoord)

    # We embed fonts for names and other overlay.  But if there are non-latin
    # characters (e.g., CJK) in names, then the embedded font is quite large.
    # Subsetting requires https://pypi.org/project/fonttools
    # Note: In theory, this could muck around with fonts from the source
    # (i.e., if they were NOT subsetted).  Does not happen with LaTeX.
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
