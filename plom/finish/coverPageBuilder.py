# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen

from plom.misc_utils import local_now_to_simple_string
import fitz
import numpy as np


def makeCover(test_num, sname, sid, tab, pdfname, *, solution=False, footer=True):
    """Create html page of name ID etc and table of marks.

    Args:
        test_num (int): the test number for the test we are making the cover for.
        sname (str): student name.
        sid (str): student id.
        tab (list): information about the test that should be put on the coverpage.
        pdfname (pathlib.Path): filename to save the pdf into

    Keyword Args:
        solution (bool): whether or not this is a cover page for solutions
        footer (bool): whether to print a footer with timestamp
    """
    m = 50  # margin
    w = 75  # box width
    w_label = 125  # label box width

    cover = fitz.open()
    hdisp = fitz.Rect(w, 0, w, 0)
    hdisp_label = fitz.Rect(w_label, 0, w_label, 0)
    vdisp = fitz.Rect(0, 25, 0, 25)
    align = fitz.TEXT_ALIGN_CENTER
    fontsize = 14

    page = cover.new_page()
    tw = fitz.TextWriter(page.rect)
    if solution:
        text = "Solutions:"
    else:
        text = "Results:"
    tw.append((m, 75), text, fontsize=fontsize)
    text = f"\N{Bullet} Name: {sname}"
    tw.append((m + w, 75), text, fontsize=fontsize)
    text = f"\N{Bullet} ID: {sid}"
    tw.append((m + w, 100), text, fontsize=fontsize)
    text = f"\N{Bullet} Test number: {test_num}"
    tw.append((m + w, 125), text, fontsize=fontsize)

    # Drawing the header
    if solution:
        headers = ["question", "version", "mark out of"]
    else:
        headers = ["question", "version", "mark", "out of"]

    shape = page.new_shape()

    rect0 = [fitz.Rect(m, 150, m + w_label, 175)] + [
        fitz.Rect(m, 150, m + w, 175) + hdisp_label + hdisp * j
        for j in range(len(headers) - 1)
    ]

    for j, (r, header) in enumerate(zip(rect0, headers)):
        shape.draw_rect(r)
        excess = tw.fill_textbox(r, header, align=align, fontsize=fontsize)
        assert not excess, f'Table header "{header}" too long for box'

    for i, row in enumerate(tab):
        if solution:
            row = (row[0], row[1], row[3])
        rects = [r + vdisp * (i + 1) for r in rect0]
        for j, (txt, r) in enumerate(zip(row, rects)):
            shape.draw_rect(r)
            excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
            assert not excess, f'Table entry "{txt}" too long for box'

    # Draw the totals row
    rects = [r + vdisp * (len(tab) + 1) for r in rect0]
    if solution:
        t = ["total", ".", sum([row[3] for row in tab])]
    else:
        t = ["total", ".", sum([row[2] for row in tab]), sum([row[3] for row in tab])]
    for j, (r, txt) in enumerate(zip(rects, t)):
        shape.draw_rect(r)
        excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
        assert not excess, f'Table entry "{txt}" too long for box'

    shape.finish(width=0.3, color=(0, 0, 0))
    shape.commit()

    if footer:
        # Last words
        text = "Cover page produced on {}".format(local_now_to_simple_string())
        p = fitz.Point(m, page.rect.height - m)
        tw.append(p, text, fontsize=fontsize)

    tw.write_text(page)

    cover.subset_fonts()

    cover.save(pdfname, garbage=4, deflate=True, clean=True)
    cover.close()
