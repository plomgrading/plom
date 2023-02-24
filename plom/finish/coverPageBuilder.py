# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen

import fitz

from plom.misc_utils import local_now_to_simple_string
from .examReassembler import papersize_portrait


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
    # check all table entries that should be numbers are non-negative numbers
    for row in tab:
        for x in row[1:]:
            try:
                y = float(x)
                assert y >= 0, "Numeric data must be non-negative."
            except ValueError:
                raise AssertionError(f"Table data {x} should be numeric.")

    m = 50  # margin
    page_top = 75
    # leave some extra; we stretch to avoid single line on new page
    page_bottom = 720
    first_page_table_top = 150  # the first table starts below some info
    extra_sep = 2  # some extra space for double hline near header
    w = 70  # box width
    w_label = 120  # label box width
    deltav = 20  # how much vertical space for each row

    cover = fitz.open()
    align = fitz.TEXT_ALIGN_CENTER
    fontsize = 12
    big_font = 14

    paper_width, paper_height = papersize_portrait
    page = cover.new_page(width=paper_width, height=paper_height)
    tw = fitz.TextWriter(page.rect)
    if solution:
        text = "Solutions"
    else:
        text = "Results"
    bullet = "\N{Bullet}"
    tw.append((m, page_top), text, fontsize=big_font)
    text = f"{bullet} Name: {sname}"
    tw.append((m + w, page_top), text, fontsize=big_font)
    text = f"{bullet} ID: {sid}"
    tw.append((m + w, page_top + 25), text, fontsize=big_font)
    text = f"{bullet} Test number: {test_num}"
    tw.append((m + w, page_top + 50), text, fontsize=big_font)

    if solution:
        tab = [[row[0], row[1], row[3]] for row in tab]
        headers = ["question", "version", "mark out of"]
        totals = ["total", ".", sum([row[2] for row in tab])]
    else:
        headers = ["question", "version", "mark", "out of"]
        totals = [
            "total",
            ".",
            sum([row[2] for row in tab]),
            sum([row[3] for row in tab]),
        ]

    shape = page.new_shape()

    # rectangles for header that we will shift downwards as we go
    def make_boxes(v1):
        v2 = v1 + deltav
        return [fitz.Rect(m, v1, m + w_label, v2)] + [
            fitz.Rect(m + w_label + w * j, v1, m + w_label + w * (j + 1), v2)
            for j in range(len(headers) - 1)
        ]

    vpos = first_page_table_top
    page_row = 0
    for j, row in enumerate(tab):
        if page_row == 0:
            # Draw the header
            for header, r in zip(headers, make_boxes(vpos)):
                shape.draw_rect(r)
                excess = tw.fill_textbox(r, header, align=align, fontsize=fontsize)
                assert not excess, f'Table header "{header}" too long for box'
            vpos += deltav + extra_sep
            page_row += 1

        for txt, r in zip(row, make_boxes(vpos)):
            shape.draw_rect(r)
            excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
            assert not excess, f'Table entry "{txt}" too long for box'
        vpos += deltav
        page_row += 1

        if vpos > page_bottom and j < (len(tab) - 1):
            # switch to new page, unless we only have the summary row left
            # in which case stretch a little to avoid a single-line next page
            shape.finish(width=0.3, color=(0, 0, 0))
            shape.commit()
            text = "Table continues on next page..."
            p = fitz.Point(m, page.rect.height - m)
            tw.append(p, text, fontsize=fontsize)
            tw.write_text(page)
            page = cover.new_page(width=paper_width, height=paper_height)
            tw = fitz.TextWriter(page.rect)
            shape = page.new_shape()
            vpos = page_top
            page_row = 0

    # Draw the final totals row
    for txt, r in zip(totals, make_boxes(vpos + extra_sep)):
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
