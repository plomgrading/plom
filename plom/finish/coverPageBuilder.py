# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022-2024 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

import pathlib
from typing import Any

import fitz

from plom.misc_utils import local_now_to_simple_string
from .examReassembler import papersize_portrait


def makeCover(
    tab: list[list[Any]],
    pdfname: pathlib.Path,
    *,
    exam_name: str | None = None,
    test_num: str | int | None = None,
    info: tuple[str | None, str | None] | None = None,
    solution: bool = False,
    footer: bool = True,
) -> None:
    """Create html page of name ID etc and table of marks.

    Args:
        tab: information about the test that should be put on the
            coverpage.  A list of lists where each row is
            ``[qlabel, ver, mark, maxPossibleMark]`` if not solutions or
            ``[qlabel, ver, maxPossibleMark]`` if solutions.
        pdfname: filename to save the pdf into.

    Keyword Args:
        exam_name: the "long name" of this assessment.
        test_num: the test number for which we are making a cover, or
            ``None`` to omit.
        info: currently a 2-tuple/2-list of student name (str)
            and student id (str).
        solution: whether or not this is a cover page for solutions.
        footer: whether to print a footer with timestamp.

    Returns:
        None
    """
    # check all table entries that should be numbers are non-negative numbers
    for row in tab:
        if solution:
            assert len(row) == 3
        else:
            assert len(row) == 4
        assert isinstance(
            row[0], str
        ), f'First row entry should be a string but we got "{row}"'
        for x in row[1:]:
            try:
                y = float(x)
                assert y >= 0, "Numeric data must be non-negative."
            except (TypeError, ValueError):
                raise AssertionError(f"Table data {x} should be numeric.")

    m = 50  # margin
    page_top = 75
    # leave some extra; we stretch to avoid single line on new page
    page_bottom = 700
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

    vpos = page_top
    tw = fitz.TextWriter(page.rect)
    if exam_name:
        tw.append((m, vpos), exam_name, fontsize=big_font)
        vpos += deltav
        vpos += deltav // 2
    if solution:
        text = "Solutions"
    else:
        text = "Results"
    tw.append((m, vpos), text, fontsize=big_font)
    bullet = "\N{BULLET}"
    if info:
        sname, sid = info
        if sname is None:
            sname = "Not ID'd yet"
        if sid is None:
            sid = "Not ID'd yet"
        tw.append((m + 100, vpos), f"{bullet} Name: {sname}", fontsize=big_font)
        vpos += deltav
        tw.append((m + 100, vpos), f"{bullet} ID: {sid}", fontsize=big_font)
        vpos += deltav
    if test_num is not None:
        if isinstance(test_num, int):
            text = f"{bullet} Test number: {test_num:04}"
        else:
            text = f"{bullet} Test number: {test_num}"
        tw.append((m + 100, vpos), text, fontsize=big_font)
        vpos += deltav

    if solution:
        headers = ["question", "version", "mark out of"]
        totals = ["total", "", sum([row[2] for row in tab])]
    else:
        headers = ["question", "version", "mark", "out of"]
        totals = [
            "total",
            "",
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
