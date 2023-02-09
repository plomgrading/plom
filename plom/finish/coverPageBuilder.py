# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen

from plom.misc_utils import local_now_to_simple_string
import fitz
import logging
logging.basicConfig(level = logging.DEBUG)

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
    vdisp = fitz.Rect(0, 50, 0, 50)
    align = 1 #centre 
    fontsize = 14

    page = cover.new_page()
    p = fitz.Point(50, 75)  # start point of 1st line
    text = "Results: \n \u2022 Name = {} \n \u2022 ID = {} \n \u2022 Test number = {}".format(sname, sid, test_num)
    page.insert_text(p, text,  fontname = "helv", fontsize = fontsize)

    shape = page.new_shape()
    # Drawing the header with question, version, mark, outof
    r = [fitz.Rect(50, 200, 125, 250) + hdisp * j for j in range(0, 4)]
    t = ["question", "version", "mark", "out of"]    
    for j in range(0, 4):
        shape.draw_rect(r[j])
        shape.insert_textbox(r[j], t[j], align = align, fontsize = fontsize)

    # Drawing the tab
    for i in range(0, len(tab)):
        r = [r[j] + vdisp for j in range(0,4)]
        for j in range(0, 4):
            shape.draw_rect(r[j])
            shape.insert_textbox(r[j], str(tab[i][j]), align = align, fontsize = fontsize)

    # Drawing the rest
    r = [r[j] + vdisp for j in range(0,4)]
    t = ["total", ".", sum([tab[i][2] for i in range(0, len(tab))]), sum([tab[i][3] for i in range(0, len(tab))])]
    for j in range(0, 4):
        shape.draw_rect(r[j])
        shape.insert_textbox(r[j], str(t[j]), align = 1, fontsize = fontsize) 

    shape.finish(width = 0.3, color = (0, 0, 0))
    shape.commit()
    
    # Last words
    text = "Cover page produced on {}".format(local_now_to_simple_string())
    p = fitz.Point(50, page.rect.height - 50)
    page.insert_text(p, text,  fontname = "helv", fontsize = fontsize)

    cover.save(pdfname)
    cover.close()

    