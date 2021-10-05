# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import tempfile
from pathlib import Path

from PIL import Image
import fitz

from plom import __version__

# hardcoded for letter, https://gitlab.com/plom/plom/issues/276
papersize_portrait = (612, 792)
papersize_landscape = (792, 612)
margin = 10


def reassemble(outname, shortName, sid, coverfile, id_images, marked_pages, dnm_images):
    """Reassemble a pdf from the cover and question images.

    args:
        outname (str/pathlib.Path): name of a PDF file to write.
        shortName (str): The name of the exam, written into metadata.
        sid (str): Student ID, to be written into metadata.
        coverfile (str/pathlib.Path): a coversheet already in PDF format.
            Pass None to omit (deprecated "totalling mode" did this).
        id_images (list): str/Path images to be inserted one per page.
        marked_pages (list): str/Path images to be inserted one per page.
        dnm_images (list): str/Path images to be combined into a new
            final page.

    return:
        bool: True if successful or False if PDF file already exists.
            Note: no attempt is made to check if its correct; merely
            that it exists.
    """
    outname = Path(outname)
    if outname.exists():
        return False

    exam = fitz.open()
    if coverfile:
        exam.insertPDF(fitz.open(coverfile))

    for img_name in [*id_images, *marked_pages]:
        img_name = Path(img_name)
        png_size = img_name.stat().st_size
        im = Image.open(img_name)

        # Rotate page not the image: we want landscape on screen
        if im.width > im.height:
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait
        pg = exam.newPage(width=w, height=h)
        rec = fitz.Rect(margin, margin, w - margin, h - margin)

        # Make a jpeg in memory, and use that if its significantly smaller
        with tempfile.SpooledTemporaryFile(mode="w+b", suffix=".jpg") as jpeg_file:
            im.convert("RGB").save(
                jpeg_file, format="jpeg", quality=90, optimize=True, subsampling=0
            )
            jpeg_size = jpeg_file.tell()  # cannot use stat as above
            if jpeg_size < 0.75 * png_size:
                # print("Using smaller JPEG for {}".format(img_name))
                jpeg_file.seek(0)
                pg.insert_image(rec, stream=jpeg_file.read())
            else:
                pg.insert_image(rec, filename=img_name)

    if len(dnm_images) > 1:
        w, h = papersize_landscape
    else:
        w, h = papersize_portrait
    if dnm_images:
        pg = exam.newPage(width=w, height=h)
        W = (w - 2 * margin) // len(dnm_images)
        header_bottom = margin + h // 10
        offset = margin
        for f in dnm_images:
            rect = fitz.Rect(offset, header_bottom, offset + W, h - margin)
            pg.insert_image(rect, filename=f)
            offset += W
        if len(dnm_images) > 1:
            text = 'These pages were flagged "Do No Mark" by the instructor.'
        else:
            text = 'This page was flagged "Do No Mark" by the instructor.'
        text += "  In most cases nothing here was marked."
        r = pg.insert_textbox(
            fitz.Rect(margin, margin, w - margin, header_bottom),
            text,
            fontsize=12,
            color=[0, 0, 0],
            fontname="Helvetica",
            fontfile=None,
            align="left",
        )
        assert r > 0

    exam.setMetadata(
        {
            "title": "{} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    exam.save(outname, deflate=True)
    return True
