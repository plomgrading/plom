# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee

import tempfile
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
        dict: The keys index the corners and each value is a
            `pathlib.Path` for a PNG file for that corner's QR code.
            The corners are indexed counterclockwise by:

            index | meaning
            ------|--------
            1     | top-right
            2     | top-left
            3     | bottom-left
            4     | bottom-right
    """
    qr_file = {}

    for corner_index in range(1, 5):
        tpv = encodeTPV(papernum, pagenum, ver, corner_index, code)
        filename = dur / f"qr_{papernum:04}_pg{pagenum}_{corner_index}.png"

        # qr_code = pyqrcode.create(tpv, error="H")
        # qr_code.png(filename, scale=4)

        qr_code = segno.make(tpv, error="H")
        qr_code.save(filename, scale=4)

        qr_file[corner_index] = filename

    return qr_file


def create_exam_and_insert_QR(
    spec,
    papernum,
    question_versions,
    qr_file,
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
        qr_file (dict): a dict of dicts.  The outer keys are integer
            page numbers.  The inner keys index the corners, giving a
            path to an image of the appropriate QR code.
            TODO: consider calling the QR builder from here.

    Keyword Arguments:
        no_qr (bool): whether to paste in QR-codes (default: False)
            Note backward logic: False means yes to QR-codes.

    Returns:
        fitz.Document: PDF document.
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

    page_width = exam[0].bound().width
    page_height = exam[0].bound().height

    # create two "do not write" (DNW) rectangles accordingly with TL (top left) and TR (top right)
    rDNW_TL = fitz.Rect(15, 15, 90, 90)
    rDNW_TR = fitz.Rect(page_width - 90, 15, page_width - 15, 90)

    # 70x70 page-corner boxes for the QR codes
    # TL: Top Left, TR: Top Right, BL: Bottom Left, BR: Bottom Right
    TL = fitz.Rect(15, 20, 85, 90)
    TR = fitz.Rect(page_width - 85, 20, page_width - 15, 90)
    BL = fitz.Rect(15, page_height - 90, 85, page_height - 20)
    BR = fitz.Rect(page_width - 85, page_height - 90, page_width - 15, page_height - 20)

    for page_index in range(spec["numberOfPages"]):
        # Workaround Issue #1347: unnecessary for pymupdf>=1.18.7
        exam[page_index].clean_contents()
        # papernum.page-name.pagenum stamp in top-centre of page
        rect = fitz.Rect(page_width // 2 - 70, 20, page_width // 2 + 70, 46)
        # name of the group to which page belongs
        group = page_to_group[page_index + 1]
        text = "{} {} {}".format(
            f"{papernum:04}", group.ljust(5), f"p. {page_index + 1}"
        )
        excess = exam[page_index].insert_textbox(
            rect,
            text,
            fontsize=18,
            color=[0, 0, 0],
            fontname="Helvetica",
            fontfile=None,
            align=1,
        )
        assert excess > 0, "Text didn't fit: is paper number label too long?"
        exam[page_index].draw_rect(rect, color=[0, 0, 0])

        if no_qr:
            # no more processing of this page if QR codes unwanted
            continue

        # stamp DNW near staple: even/odd pages different
        # Top Left for even pages, Top Right for odd pages
        # TODO: Perhaps this process could be improved by putting
        # into functions
        rDNW = rDNW_TL if page_index % 2 == 0 else rDNW_TR
        shape = exam[page_index].new_shape()
        shape.draw_line(rDNW.top_left, rDNW.top_right)
        if page_index % 2 == 0:
            shape.draw_line(rDNW.top_right, rDNW.bottom_left)
        else:
            shape.draw_line(rDNW.top_right, rDNW.bottom_right)
        shape.finish(width=0.5, color=[0, 0, 0], fill=[0.75, 0.75, 0.75])
        shape.commit()
        if page_index % 2 == 0:
            # offset by trial-and-error, could be improved
            rDNW = rDNW + (19, 19, 19, 19)
        else:
            rDNW = rDNW + (-19, 19, -19, 19)
        mat = fitz.Matrix(45 if page_index % 2 == 0 else -45)
        pivot = rDNW.tr / 2 + rDNW.bl / 2
        morph = (pivot, mat)
        excess = exam[page_index].insert_textbox(
            rDNW,
            spec["name"],
            fontsize=8,
            fontname="Helvetica",
            fontfile=None,
            align=1,
            morph=morph,
        )
        assert excess > 0, "Text didn't fit: shortname too long? font issue?"

        # paste in the QR-codes
        # Grab the tpv QRcodes for current page and put them on the pdf
        # Remember that we only add 3 of the 4 QR codes for each page since
        # we always have a corner section for staples and such
        qr_code = {}
        for corner_index in range(1, 5):
            qr_code[corner_index] = fitz.Pixmap(qr_file[page_index + 1][corner_index])
        # Note: draw png first so it doesn't occlude the outline
        if page_index % 2 == 0:
            exam[page_index].insert_image(TR, pixmap=qr_code[1], overlay=True)
            exam[page_index].draw_rect(TR, color=[0, 0, 0], width=0.5)
        else:
            exam[page_index].insert_image(TL, pixmap=qr_code[2], overlay=True)
            exam[page_index].draw_rect(TL, color=[0, 0, 0], width=0.5)
        exam[page_index].insert_image(BL, pixmap=qr_code[3], overlay=True)
        exam[page_index].insert_image(BR, pixmap=qr_code[4], overlay=True)
        exam[page_index].draw_rect(BL, color=[0, 0, 0], width=0.5)
        exam[page_index].draw_rect(BR, color=[0, 0, 0], width=0.5)

    for ver, pdf in pdf_version.items():
        pdf.close()
    return exam


def is_possible_to_encode_as(s, encoding):
    """Is it possible to encode this string in this particular encoding?

    Arguments:
        s (str): a string.
        encoding (str): Encoding type.

    Returns:
        bool
    """
    try:
        s.encode(encoding)
        return True
    except UnicodeEncodeError:
        return False


def insert_extra_info(extra, exam, x=None, y=None):
    """Creates the extra info (usually student name and id) boxes and places them in the first page.

    Arguments:
        extra (dict): dictionary with student id and name.
        exam (fitz.Document): PDF document.
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
            and 100 is the bottom of the page.  If None, defaults to 42.5
            for historical reasons.

    Raises:
        ValueError: Raise error if the student name and number is not encodable.

    Returns:
        fitz.Document: the exam object from the input, but with the extra
            info added into the first page.
    """
    if x is None:
        x = 50
    if y is None:
        y = 42.5

    page_width = exam[0].bound().width
    page_height = exam[0].bound().height

    student_id = extra["id"]
    student_name = extra["name"]
    txt = "{}\n{}".format(student_id, student_name)
    sign_here = "Please sign here"

    box_width = (
        max(
            fitz.get_text_length(student_id, fontsize=36, fontname="Helvetica"),
            fitz.get_text_length(student_name, fontsize=36, fontname="Helvetica"),
            fitz.get_text_length(sign_here, fontsize=48, fontname="Helvetica"),
        )
        * 1.11  # magic: just til it covers IDbox2
    )
    box1_height = 2 * 36 * 1.5  # two lines of 36 pt and baseline
    box2_height = 48 * 1.6

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
    exam[0].draw_rect(name_id_rect, color=[0, 0, 0], fill=[1, 1, 1], width=2)
    exam[0].draw_rect(signature_rect, color=[0, 0, 0], fill=[1, 1, 1], width=2)

    # TODO: This could be put into one function
    if is_possible_to_encode_as(txt, "Latin-1"):
        fontname = "Helvetica"
    elif is_possible_to_encode_as(txt, "gb2312"):
        # TODO: Double-check encoding name.  Add other CJK (how does Big5
        # vs GB work?).  Check printers can handle these or do we need to
        # embed a font?  (Adobe Acrobat users need to download something)
        fontname = "china-ss"
    else:
        # TODO: instead we could warn, use Helvetica, and get "?????" chars
        raise ValueError("Don't know how to write name {} into PDF".format(txt))

    # We insert the student name and id text box
    excess = exam[0].insert_textbox(
        name_id_rect,
        txt,
        fontsize=36,
        color=[0, 0, 0],
        fontname=fontname,
        fontfile=None,
        align=1,
    )
    assert excess > 0, "Text didn't fit: student name too long?"

    excess = exam[0].insert_textbox(
        signature_rect,
        sign_here,
        fontsize=48,
        color=[0.9, 0.9, 0.9],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    assert excess > 0

    return exam


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
    # from spec get the mapping from page to version
    page_to_version = build_page_to_version_dict(spec, question_versions)

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
        # create QR codes for each test/page/version
        qr_file = {}
        if not no_qr:
            for pg in range(1, spec["numberOfPages"] + 1):
                ver = page_to_version[pg]
                qr_file[pg] = create_QR_codes(
                    papernum, pg, ver, spec["publicCode"], Path(tmp_dir)
                )

        # We then create the exam pdf while adding the QR codes to it
        exam = create_exam_and_insert_QR(
            spec,
            papernum,
            question_versions,
            qr_file,
            no_qr=no_qr,
        )

    # If provided with student name and id, preprint on cover
    if extra:
        exam = insert_extra_info(extra, exam, xcoord, ycoord)

    # Add the deflate option to compress the embedded pngs
    # see https://pymupdf.readthedocs.io/en/latest/document/#Document.save
    # also do garbage collection to remove duplications within pdf
    # and try to clean up as much as possible.
    # `linear=True` causes https://gitlab.com/plom/plom/issues/284

    # Also worth noting that this will automatically overwrite any files
    # in the same directory that have the same name.
    exam.save(save_name, garbage=4, deflate=True, clean=True)
    exam.close()
