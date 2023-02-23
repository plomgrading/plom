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


def makeCover(test_num, sname, sid, tab, pdfname, solution=False):
    """Create html page of name ID etc and table of marks.

    Args:
        test_num (int): the test number for the test we are making the cover for.
        sname (str): student name.
        sid (str): student id.
        tab (list): information about the test that should be put on the coverpage.
        pdfname (pathlib.Path): filename to save the pdf into
        solution (bool): whether or not this is a cover page for solutions
    """
    m = 50  # margin
    w = 75  # box width

    cover = fitz.open()
    hdisp = fitz.Rect(w, 0, w, 0)
    vdisp = fitz.Rect(0, 25, 0, 25)
    align = 1  # centre
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
        t = ["question", "version", "mark out of"]
    else:
        t = ["question", "version", "mark", "out of"]
    shape = page.new_shape()

    r = [fitz.Rect(m, 150, m + w, 175) + hdisp * j for j in range(len(t))]

    for j in range(0, len(t)):
        shape.draw_rect(r[j])
        tw.fill_textbox(r[j], t[j], align=align, fontsize=fontsize)

    # Draw the table
    tab = np.array(tab)
    if solution:
        tab = tab[:, [0, 1, 3]]

    for i in range(0, tab.shape[0]):
        r = [r[j] + vdisp for j in range(0, tab.shape[1])]
        for j in range(0, tab.shape[1]):
            shape.draw_rect(r[j])
            tw.fill_textbox(r[j], str(tab[i][j]), align=align, fontsize=fontsize)

    # Draw the totals row
    r = [r[j] + vdisp for j in range(0, tab.shape[1])]
    t = ["total", ".", sum([int(tab[i][2]) for i in range(0, tab.shape[0])])]
    if not solution:
        t.append(sum([int(tab[i][3]) for i in range(0, tab.shape[0])]))
    for j in range(0, tab.shape[1]):
        shape.draw_rect(r[j])
        tw.fill_textbox(r[j], str(t[j]), align=align, fontsize=fontsize)

    shape.finish(width=0.3, color=(0, 0, 0))
    shape.commit()

    # Last words
    text = "Cover page produced on {}".format(local_now_to_simple_string())
    p = fitz.Point(m, page.rect.height - m)
    tw.append(p, text, fontsize=fontsize)
    tw.write_text(page)

    cover.subset_fonts()

    cover.save(pdfname, garbage=4, deflate=True, clean=True)
    cover.close()
