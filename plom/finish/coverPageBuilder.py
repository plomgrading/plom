# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022-2024 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih
# Copyright (C) 2023 Tam Nguyen
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen

import pathlib
from copy import deepcopy
from typing import Any

import pymupdf

from plom.misc_utils import local_now_to_simple_string, pprint_score


def make_cover(
    tab: list[list[Any]],
    pdfname: pathlib.Path,
    *,
    exam_name: str | None = None,
    paper_num: str | int | None = None,
    info: tuple[str | None, str | None] | None = None,
    solution: bool = False,
    footer: bool = True,
    papersize: str = "",
) -> None:
    """Create html page of name ID etc and table of marks.

    Args:
        tab: information about the paper that should be put on the
            coverpage.  A list of lists where each row is
            ``[qlabel, ver, mark, maxPossibleMark]`` if not solutions or
            ``[qlabel, ver, maxPossibleMark]`` if solutions.
        pdfname: filename to save the pdf into.

    Keyword Args:
        exam_name: the "long name" of this assessment.
        paper_num: the paper number for which we are making a cover, or
            ``None`` to omit.
        info: currently a 2-tuple/2-list of student name (str)
            and student id (str).
        solution: whether or not this is a cover page for solutions.
        footer: whether to print a footer with timestamp.
        papersize: a string describing the paper size.  If omitted or
            empty, use "letter" as the default.

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

    # calculate additional table rows before casting marks to str
    if solution:
        headers = ["question", "version", "mark out of"]
        totals = ["total", "", str(sum([row[2] for row in tab]))]
    else:
        headers = ["question", "version", "mark", "out of"]
        totals = [
            "total",
            "",
            pprint_score(sum([row[2] for row in tab])),
            str(sum([row[3] for row in tab])),
        ]
    # writer likes strings, cast table contents as str, but first make a copy
    tab = deepcopy(tab)
    for row in tab:
        row[1] = str(row[1])  # version
        if not solution:
            row[2] = pprint_score(row[2])  # mark
            row[3] = str(row[3])  # out of
        else:
            row[2] = str(row[2])  # "mark out of"

    # paper formatting
    m = 50  # margin
    page_top = 75
    # leave some extra; we stretch to avoid single line on new page
    page_bottom = 700
    extra_sep = 2  # some extra space for double hline near header
    w = 70  # box width
    w_label = 120  # label box width
    deltav = 20  # how much vertical space for each row

    cover = pymupdf.open()
    align = pymupdf.TEXT_ALIGN_CENTER

    font = pymupdf.Font("helvetica")
    textsize = 12
    headersize = 16
    xxlsize = 20

    if not papersize:
        papersize = "letter"
    paper_width, paper_height = pymupdf.paper_size(papersize)
    page = cover.new_page(width=paper_width, height=paper_height)

    vpos = page_top

    # Style and print the assessment title, if available
    if exam_name:
        titlewriter = pymupdf.TextWriter(page.rect)
        titlewriter.color = (0, 0, 0)
        title_width = font.text_length(exam_name, xxlsize)
        x = (paper_width - title_width) / 2
        y = 100  # Near the top of the page
        titlewriter.append((x, y), exam_name, fontsize=xxlsize)
        titlewriter.write_text(page)
        vpos += 3 * xxlsize

    # Style and print the info line.
    infowriter = pymupdf.TextWriter(page.rect)
    # infowriter.color = (0,0,1)

    if solution:
        text = "Solutions"
    else:
        text = "Results"

    if info:
        text += " for "
        sname, sid = info
        if sname is None:
            text += "Unknown Student"
        else:
            nnn = [_.strip() for _ in sname.split(",")]
            nnn.reverse()
            text += " ".join(nnn)
        if sid is None:
            text += " (no ID yet)"
        else:
            text += f" ({sid})"

    info_width = font.text_length(text, xxlsize)
    x = (paper_width - info_width) / 2
    y = vpos
    infowriter.append((x, y), text, fontsize=xxlsize)
    infowriter.write_text(page)
    vpos += 3 * xxlsize // 2

    # Style and print the paper number
    pnwriter = pymupdf.TextWriter(page.rect)
    # pnwriter.color = (0,1,0)

    if isinstance(paper_num, int):
        text = f"Paper number {paper_num:04}"
    else:
        text = f"Paper number {paper_num}"
    pn_width = font.text_length(text, headersize)
    x = (paper_width - pn_width) / 2
    y = vpos
    pnwriter.append((x, y), text, fontsize=headersize)
    pnwriter.write_text(page)
    vpos += 3 * xxlsize

    # Style and print the table of scores
    tw = pymupdf.TextWriter(page.rect)

    shape = page.new_shape()

    # rectangles for header that we will shift downwards as we go
    def make_boxes(v1):
        v2 = v1 + deltav
        return [pymupdf.Rect(m, v1, m + w_label, v2)] + [
            pymupdf.Rect(m + w_label + w * j, v1, m + w_label + w * (j + 1), v2)
            for j in range(len(headers) - 1)
        ]

    page_row = 0
    for j, row in enumerate(tab):
        if page_row == 0:
            # Draw the header
            for header, r in zip(headers, make_boxes(vpos)):
                shape.draw_rect(r)
                excess = tw.fill_textbox(r, header, align=align, fontsize=textsize)
                assert not excess, f'Table header "{header}" too long for box'
            vpos += deltav + extra_sep
            page_row += 1

        for txt, r in zip(row, make_boxes(vpos)):
            shape.draw_rect(r)
            excess = tw.fill_textbox(r, txt, align=align, fontsize=textsize)
            assert not excess, f'Table entry "{txt}" too long for box'
        vpos += deltav
        page_row += 1

        if vpos > page_bottom and j < (len(tab) - 1):
            # switch to new page, unless we only have the summary row left
            # in which case stretch a little to avoid a single-line next page
            shape.finish(width=0.3, color=(0, 0, 0))
            shape.commit()
            text = "Table continues on next page..."
            p = pymupdf.Point(m, page.rect.height - m)
            tw.append(p, text, fontsize=textsize)
            tw.write_text(page)
            page = cover.new_page(width=paper_width, height=paper_height)
            tw = pymupdf.TextWriter(page.rect)
            shape = page.new_shape()
            vpos = page_top
            page_row = 0

    # Draw the final totals row
    for txt, r in zip(totals, make_boxes(vpos + extra_sep)):
        shape.draw_rect(r)
        excess = tw.fill_textbox(r, txt, align=align, fontsize=textsize)
        assert not excess, f'Table entry "{txt}" too long for box'
    shape.finish(width=0.3, color=(0, 0, 0))
    shape.commit()

    if footer:
        # Last words
        text = "Cover page produced on {}".format(local_now_to_simple_string())
        p = pymupdf.Point(m, page.rect.height - m)
        tw.append(p, text, fontsize=textsize)

    tw.write_text(page)

    cover.subset_fonts()

    cover.save(pdfname, garbage=4, deflate=True, clean=True)
    cover.close()
