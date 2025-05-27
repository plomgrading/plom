#!/usr/bin/python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Philip D Loewen
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Deep Shah

"""Generate a PDF with title text and QR codes both indicating scrap.

All parameters are optional and have sensible defaults. Saying simply
    python3 plom-make-scrap-sheets.py
will create (or overwrite!) a 2-page file named PLOM-scrap.pdf suitable
for double-sided printing and mass duplication.

Simple mode:
To make 12 sheets of scrap paper, say
    python3 plom-make-scrap-sheets.py -n 12
You will get a 24-page PDF document to print double-sided.

Fancy mode:
To mark 30 copies of your 3-page formula sheet as scrap, say
    python3 plom-make-scrap-sheets.py -n 30 -pdf myformulas.pdf
You will get a 120-page PDF document to print double-sided.
That's because your 3-page input gets padded to 4 pages to make
2 physical sheets for each recipient, and 4 times 30 makes 120.

Options:
Command-line arguments can influence the text centred on each page,
the output filename, etc. For a quick summary, say
    python3 plom-make-scrap-sheets.py --help

Power Users:
The page titles can be enhanced to include a unique integer in the
title of each packet of scrap pages. Embed the literal string {}
in the title parameter to show where the counter should appear.
You can even insert a Python integer-formatting code in those braces.
E.g., you can say
    python3 plom-make-scrap-sheets.py -t "Scrap paper (seq {:04d})" -n 5
"""

from __future__ import annotations

import argparse

import pymupdf 
import segno
import io

# Here are the corner orientation codes,
# as documented in the source file tpv_utils.py:
cnrNE = 1
cnrNW = 2
cnrSW = 3
cnrSE = 4


def stamp_page(
    PDFpage: pymupdf.Page,
    NW: str | None = None,
    NE: str | None = None,
    SE: str | None = None,
    SW: str | None = None,
    title: str | None = None,
) -> None:
    xmin, ymin, xmax, ymax = PDFpage.rect
    # print(f"(xmin,ymin,xmax,ymax) = ({xmin},{ymin},{xmax},{ymax})")

    # Introduce perimeter of h=20px, hoping this gets us into the "ImageableArea"
    # of whatever printer eventually puts this onto paper:
    h = 20  # Perhaps a smaller value could work. Trial and error?
    xmin += h
    xmax -= h
    ymin += h
    ymax -= h

    # Set the QR image size in PDF points (side length w).
    # Default micro PNG image is 21x21 pixels.
    stretch = 1.5
    w = 21 * stretch

    if NW is not None:
        QRNW = segno.make(NW, micro=True)
        NWstream = io.BytesIO()
        QRNW.save(NWstream, kind="png")

        PDFpage.insert_image(pymupdf.Rect(xmin, ymin, xmin + w, ymin + w), stream=NWstream)

    if NE is not None:
        QRNE = segno.make(NE, micro=True)
        NEstream = io.BytesIO()
        QRNE.save(NEstream, kind="png")

        PDFpage.insert_image(pymupdf.Rect(xmax - w, ymin, xmax, ymin + w), stream=NEstream)

    if SE is not None:
        QRSE = segno.make(SE, micro=True)
        SEstream = io.BytesIO()
        QRSE.save(SEstream, kind="png")

        PDFpage.insert_image(pymupdf.Rect(xmax - w, ymax - w, xmax, ymax), stream=SEstream)

    if SW is not None:
        QRSW = segno.make(SW, micro=True)
        SWstream = io.BytesIO()
        QRSW.save(SWstream, kind="png")

        PDFpage.insert_image(pymupdf.Rect(xmin, ymax - w, xmin + w, ymax), stream=SWstream)

    if title is not None:
        # Centre title between QR boxes
        tlen = pymupdf.get_text_length(title)
        PDFpage.insert_text([(xmin + xmax) / 2 - tlen / 2, ymin + w / 2], title)

    return PDFpage


def configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--copies",
        type=int,
        default=1,
        action="store",
        help="number of copies for given PDF, else number of physical sheets (default 1)",
    )
    parser.add_argument(
        "-pdf",
        "--pdf",
        type=str,
        default=None,
        action="store",
        help="filename of PDF to stamp with DNM notations (optional)",
    )
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        default="This page will not be graded!",
        help="Text to stamp at the top centre of each page (optional; default provided).\nThe special string {} can be used at most once to indicate where a unique sequence number should be included.\nEnhancing that string with a Python format code for integer variables is supported.",
    )
    parser.add_argument(
        "-O",
        "--outfile",
        type=str,
        default="PLOM-scrap.pdf",
        help="filename for output (optional, default PLOM-scrap.pdf)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        # nargs=0,
        action="store_true",
        default=False,
        help="enable debug printing (default False)",
    )
    return parser


if __name__ == "__main__":
    parser = configure_parser()
    args = parser.parse_args()

    if args.debug:
        print(f"Starting {__file__} with these arguments:")
        print(args)

    # Build a base document to decorate.
    # This must have a positive, even number of pages
    if args.pdf is not None:
        unstamped = pymupdf.Document(args.pdf)
    else:
        unstamped = pymupdf.Document()

    while len(unstamped) % 2 != 0 or len(unstamped) == 0:
        _ = unstamped.new_page(0, width=612, height=792)

    if args.debug:
        print(f"Unstamped template doc  is ready, with {len(unstamped)} pages.")

    outdoc = pymupdf.Document()
    for i in range(args.copies):
        QRmessage = f"PLOM{i:04d}"
        for p in range(len(unstamped)):
            outdoc.insert_pdf(unstamped, from_page=p, to_page=p)
            ndx = len(outdoc) - 1
            # Notice the .format(i) suffix that embeds the counter in the title string,
            # if the title string includes a substring like {} to catch the value.
            stamp_page(
                outdoc[ndx],
                title=args.title.format(i),
                NW=f"plomS{cnrNW:1d}",
                NE=f"plomS{cnrNE:1d}",
                SW=f"plomS{cnrSW:1d}",
                SE=f"plomS{cnrSE:1d}",
            )

    if args.debug:
        print(f"Stamped output document is ready, with {len(outdoc)} pages.")

    outdoc.save(args.outfile)

    if args.debug:
        print(f"Wrote {len(outdoc)} pages to {args.outfile}. Done.")

    outdoc.close()
