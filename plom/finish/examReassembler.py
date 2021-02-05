# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
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


def reassemble(outname, shortName, sid, coverfname, img_list):
    """Reassemble a pdf from the cover and question images.

    args:
        outname (str, Path): name of a PDF file to write.
        shortName (str): The name of the exam, written into metadata.
        sid (str): Student ID, to be written into metadata.
        coverfname (str, Path): a coversheet already in PDF format.
            Pass None to omit (deprecated "totalling mode" did this).
        img_list (list): list of str or Path images to be inserted one
            per page.

    return:
        bool: True if successful or False if PDF file already exists.
            Note: no attempt is made to check if its correct; merely
            that it exists.
    """
    outname = Path(outname)
    if outname.exists():
        return False

    exam = fitz.open()
    if coverfname:
        exam.insertPDF(fitz.open(coverfname))

    for img_name in img_list:
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
                # TODO: can remove str() once minimum pymupdf is 1.18.9
                pg.insert_image(rec, filename=str(img_name))

    exam.setMetadata(
        {
            "title": "{} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    exam.save(outname, deflate=True)
    return True
