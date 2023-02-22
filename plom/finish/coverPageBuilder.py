# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022 Colin B. Macdonald
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
    # hide imports until needed Issue #2231.
    cover = fitz.open()
    hdisp = fitz.Rect(75, 0, 75, 0)
    vdisp = fitz.Rect(0, 25, 0, 25)
    align = 1  # centre
    fontsize = 14

    page = cover.new_page()
    tw = fitz.TextWriter(page.rect)
    if solution == True:
        text = "Solutions:"
    else:
        text = "Results:"
    tw.append((50, 75), text, fontsize=fontsize)
    text = "\u2022 Name = {}".format(sname)
    tw.append((125, 75), text, fontsize=fontsize)
    text = "\u2022 ID = {}".format(sid)
    tw.append((125, 100), text, fontsize=fontsize)
    text = "\u2022 Test number = {}".format(test_num)
    tw.append((125, 125), text, fontsize=fontsize)

    # Drawing the header
    if solution == True:
        t = ["question", "version", "mark out of"]
    else:
        t = ["question", "version", "mark", "out of"]
    shape = page.new_shape()

    r = [fitz.Rect(50, 150, 125, 175) + hdisp * j for j in range(0, len(t))]

    for j in range(0, len(t)):
        shape.draw_rect(r[j])
        tw.fill_textbox(r[j], t[j], align=align, fontsize=fontsize)

    # Drawing the tab
    tab = np.array(tab)
    if solution == True:
        tab = tab[:, [0, 1, 3]]

    for i in range(0, tab.shape[0]):
        r = [r[j] + vdisp for j in range(0, tab.shape[1])]
        for j in range(0, tab.shape[1]):
            shape.draw_rect(r[j])
            tw.fill_textbox(r[j], str(tab[i][j]), align=align, fontsize=fontsize)

    # Drawing the rest
    r = [r[j] + vdisp for j in range(0, tab.shape[1])]
    t = ["total", ".", sum([tab[i][2] for i in range(0, tab.shape[0])])]
    if solution == False:
        t.append(sum([tab[i][3] for i in range(0, tab.shape[0])]))
    for j in range(0, tab.shape[1]):
        shape.draw_rect(r[j])
        tw.fill_textbox(r[j], str(t[j]), align=align, fontsize=fontsize)

    shape.finish(width=0.3, color=(0, 0, 0))
    shape.commit()

    # Last words
    text = "Cover page produced on {}".format(local_now_to_simple_string())
    p = fitz.Point(50, page.rect.height - 50)
    tw.append(p, text, fontsize=fontsize)
    tw.write_text(page)

    cover.subset_fonts()

    cover.save(pdfname, garbage=4, deflate=True, clean=True)
    cover.close()
