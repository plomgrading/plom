# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2025 Aidan Murphy

import tempfile
from pathlib import Path
from typing import Any

import PIL.Image
import pymupdf

from plom.finish import __version__
from plom.scan.rotate import rot_angle_from_jpeg_exif_tag


# hardcoded for letter, https://gitlab.com/plom/plom/issues/276
papersize_portrait = (612, 792)
papersize_landscape = (792, 612)
margin = 10


def reassemble(
    outname: str | Path,
    shortName: str,
    sid: str,
    coverfile: str | Path | None,
    id_images: list[dict[str, Any]],
    marked_pages: list[str],
    dnm_images,
    *,
    nonmarked_images: list[dict[str, Any]] | None = None,
):
    """Reassemble a pdf from the cover and question images.

    Args:
        outname (str/pathlib.Path): name of a PDF file to write.
        shortName (str): The name of the exam, written into metadata.
        sid (str): Student ID, to be written into metadata.
        coverfile (str/pathlib.Path): a coversheet already in PDF format.
            Pass None to omit (deprecated "totalling mode" did this).
        id_images (list): dict of images with keys "filename" (`pathlib.Path`)
            and "rotation" (`integer`).
        marked_pages (list): `pathlib.Path` for each image.
        dnm_images (list): as above ``id_images``.

    Keyword Args:
        nonmarked_images: optional list of images that were seen but not
            marked.

    Returns:
        None
    """
    outname = Path(outname)

    if coverfile:
        exam = pymupdf.open(coverfile)
    else:
        exam = pymupdf.open()

    for img in id_images:
        w, h = papersize_portrait
        pg = exam.new_page(width=w, height=h)
        rect = pymupdf.Rect(margin, margin, w - margin, h - margin)
        # pymupdf insert_image does not respect exif
        rot = rot_angle_from_jpeg_exif_tag(img["filename"])
        # now apply soft rotation
        rot += img["rotation"]
        pg.insert_image(rect, filename=img["filename"], rotate=rot)  # ccw

    for img_name in marked_pages:
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
        rec = pymupdf.Rect(margin, margin, w - margin, h - margin)

        pg.insert_image(rec, filename=img_name, rotate=angle)

    # process DNM pages one at a time, putting at most three per page
    _insert_img_list_at_3_per_page(
        exam,
        dnm_images,
        'flagged "Do No Mark" by the instructor.  '
        "In most cases nothing here was marked.",
    )

    # process nonmarked pages one at a time, putting at most three per page
    _insert_img_list_at_3_per_page(
        exam, nonmarked_images, "seen but deemed not relevant to any question."
    )

    exam.set_metadata(
        {
            "title": f"{shortName} {sid}",
            "producer": f"Plom {__version__}",
        }
    )

    exam.save(outname, deflate=True)
    exam.close()


def _insert_img_list_at_3_per_page(
    doc: pymupdf.Document, imgs: list[dict[str, Any]] | None, explanation: str
) -> None:
    if not imgs:
        return
    max_per_page = 3
    on_this_page = 0
    W = 0  # defined later, false positive from pylint
    N = len(imgs)
    for idx, img in enumerate(imgs):
        how_many_more = N - idx
        if on_this_page == 0:
            if how_many_more > 1:
                # two or more pages remain, do a landscape page
                w, h = papersize_landscape
            else:
                w, h = papersize_portrait
            pg = doc.new_page(width=w, height=h)
            # width of each image on the page
            W = (w - 2 * margin) // min(max_per_page, how_many_more)
            header_bottom = margin + h // 10
            offset = margin
            text = "These pages were " if how_many_more > 1 else "This page was "
            text += explanation
            r = pg.insert_textbox(
                pymupdf.Rect(margin, margin, w - margin, header_bottom),
                text,
                fontsize=12,
                color=(0, 0, 0),
                align="left",
            )
            assert r > 0
        rect = pymupdf.Rect(offset, header_bottom, offset + W, h - margin)
        # pymupdf insert_image does not respect exif
        rot = rot_angle_from_jpeg_exif_tag(img["filename"])
        # now apply soft rotation
        rot += img["rotation"]
        pg.insert_image(rect, filename=img["filename"], rotate=rot)  # ccw
        offset += W
        on_this_page += 1
        if on_this_page == max_per_page:
            on_this_page = 0


def _unused_in_memory_jpeg_conversion(img_name, pg, rec):
    # TODO: useful bit of transcoding-in-memory code
    # Its not currently used b/c clients try jpeg themselves now

    png_size = img_name.stat().st_size
    im = PIL.Image.open(img_name)
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
