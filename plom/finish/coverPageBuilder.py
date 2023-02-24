# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen

import fitz

from plom.misc_utils import local_now_to_simple_string


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
    w = 75  # box width
    w_label = 125  # label box width

    cover = fitz.open()
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
    rect0 = [fitz.Rect(m, 150, m + w_label, 175)] + [
        fitz.Rect(m + w_label + w * j, 150, m + w_label + w * (j + 1), 175)
        for j in range(len(headers) - 1)
    ]

    # Draw the header
    for r, header in zip(rect0, headers):
        shape.draw_rect(r)
        excess = tw.fill_textbox(r, header, align=align, fontsize=fontsize)
        assert not excess, f'Table header "{header}" too long for box'

    if len(tab) <= 21:  # keep on one page
        for i, row in enumerate(tab):
            rects = [r + vdisp * (i + 1) for r in rect0]
            for txt, r in zip(row, rects):
                shape.draw_rect(r)
                excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
                assert not excess, f'Table entry "{txt}" too long for box'
        # Draw the final totals row
        rects = [r + vdisp * (len(tab) + 1) for r in rect0]
        for r, txt in zip(rects, totals):
            shape.draw_rect(r)
            excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
            assert not excess, f'Table entry "{txt}" too long for box'
        shape.finish(width=0.3, color=(0, 0, 0))
        shape.commit()

    else:  # split onto two pages
        for i, row in enumerate(tab[:20]):
            rects = [r + vdisp * (i + 1) for r in rect0]
            for txt, r in zip(row, rects):
                shape.draw_rect(r)
                excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
                assert not excess, f'Table entry "{txt}" too long for box'
        shape.finish(width=0.3, color=(0, 0, 0))
        shape.commit()

        text = "Table continues on next page..."
        p = fitz.Point(m, page.rect.height - m)
        tw.append(p, text, fontsize=fontsize)
        tw.write_text(page)

        # now go on to page 2.

        page = cover.new_page()
        tw = fitz.TextWriter(page.rect)
        shape = page.new_shape()
        # Redraw the header
        for r, header in zip(rect0, headers):
            shape.draw_rect(r)
            excess = tw.fill_textbox(r, header, align=align, fontsize=fontsize)
        assert not excess, f'Table header "{header}" too long for box'
        for i, row in enumerate(tab[20:]):
            rects = [r + vdisp * (i + 1) for r in rect0]
            for txt, r in zip(row, rects):
                shape.draw_rect(r)
                excess = tw.fill_textbox(r, str(txt), align=align, fontsize=fontsize)
                assert not excess, f'Table entry "{txt}" too long for box'
        # Draw the final totals row
        rects = [r + vdisp * (len(tab) + 1) for r in rect0]
        for r, txt in zip(rects, totals):
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
