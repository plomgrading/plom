# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import tempfile
from pathlib import Path

import exif
import fitz
import PIL.Image


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
        None
    """
    outname = Path(outname)

    if coverfile:
        exam = fitz.open(coverfile)
    else:
        exam = fitz.open()

    for img_name in [*id_images, *marked_pages]:
        img_name = Path(img_name)
        im = PIL.Image.open(img_name)

        # Rotate page not the image: we want landscape on screen
        if im.width > im.height:
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait

        # but if image has a exif metadata rotation, then swap
        angle = rot_angle_from_jpeg_exif_tag(img_name)
        if angle in (90, -90):
            w, h = h, w

        pg = exam.new_page(width=w, height=h)
        rec = fitz.Rect(margin, margin, w - margin, h - margin)

        pg.insert_image(rec, filename=img_name, rotate=angle)

        # TODO: useful bit of transcoding-in-memory code here: move somewhere!
        # Its not currently useful here b/c clients try jpeg themeselves now
        continue

        png_size = img_name.stat().st_size
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
        pg = exam.new_page(width=w, height=h)
        W = (w - 2 * margin) // len(dnm_images)
        header_bottom = margin + h // 10
        offset = margin
        for img_name in dnm_images:
            rect = fitz.Rect(offset, header_bottom, offset + W, h - margin)
            rot = rot_angle_from_jpeg_exif_tag(img_name)
            pg.insert_image(rect, filename=img_name, rotate=rot)
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
            color=(0, 0, 0),
            align="left",
        )
        assert r > 0

    exam.set_metadata(
        {
            "title": "{} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    exam.save(outname, deflate=True)
    # https://gitlab.com/plom/plom/-/issues/1777
    exam.close()


def rot_angle_from_jpeg_exif_tag(img_name):
    """If we have a jpeg and it has exif orientation data, return angle.

    If not a jpeg, then return 0.
    """
    if img_name.suffix not in (".jpg", ".jpeg"):
        return 0
    with open(img_name, "rb") as f:
        im = exif.Image(f)
    if not im.has_exif:
        return 0
    o = im.get("orientation")
    if o is None:
        return 0
    # print(f"{img_name} has exif orientation: {o}")
    if o == exif.Orientation.TOP_LEFT:
        return 0
    elif o == exif.Orientation.RIGHT_TOP:
        return -90
    elif o == exif.Orientation.BOTTOM_RIGHT:
        return 180
    elif o == exif.Orientation.LEFT_BOTTOM:
        return 90
    else:
        raise NotImplementedError(f"Unexpected exif orientation: {o}")
