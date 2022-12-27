# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
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


def assemble(outname, shortName, sid, coverfile, img_list, watermark=False):
    """Assemble a pdf from the solution images.

    args:
        outname (str, Path): name of a PDF file to write.
        shortName (str): The name of the exam, written into metadata.
        coverfile (str/pathlib.Path): a coversheet already in PDF format.
        sid (str): Student ID, to be written into metadata.
        img_list (list): list of str or Path images to be inserted one
            per page.
        watermark (bool): whether to watermark soln pages with student id.

    return:
        None
    """
    outname = Path(outname)

    if coverfile:
        exam = fitz.open(coverfile)
    else:
        exam = fitz.open()

    for img_name in img_list:
        img_name = Path(img_name)
        png_size = img_name.stat().st_size
        im = Image.open(img_name)

        # Rotate page not the image: we want landscape on screen
        if im.width > im.height:
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait
        pg = exam.new_page(width=w, height=h)
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
            # add a watermark of the student-id in rect at bottom of page
        if watermark:
            wm_rect = fitz.Rect(margin, h - margin - 24, margin + 200, h - margin)
            text = f"produced for {sid}"
            excess = pg.insert_textbox(
                wm_rect,
                text,
                fontsize=18,
                color=(0, 0, 0),
                align=1,
                stroke_opacity=0.33,
                fill_opacity=0.33,
                overlay=True,
            )
            assert excess > 0, "Text didn't fit: is SID label too long?"
            pg.draw_rect(wm_rect, color=[0, 0, 0], stroke_opacity=0.25)

    exam.set_metadata(
        {
            "title": "Solutions for {} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    exam.save(outname, deflate=True)
    # https://gitlab.com/plom/plom/-/issues/1777
    exam.close()
