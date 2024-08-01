#!/usr/bin/python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Philip D Loewen

"""Generate a PDF with Do Not Mark text and QR codes.

Simple mode: To make 12 sheets of scrap paper, say
    python3 plom-make-DNM-sheets.py -n 12
You will get a 24-page PDF document to print double-sided.

Fancy mode: To decorate 30 copies of your 3-page formula sheet, say
    python3 plom-make-DNM-sheets.py -n 30 -pdf myformulas.pdf
You will get a 120-page PDF document to print double-sided.
That's 30 copies of the 4-page (2-sheet) PDF produced by padding
your input so that each recipient gets 2 physical sheets of paper.

Options: Command-line arguments can influence the text centred on each page,
the codes embedded in the QR corners, the output filename, etc. For details,
read the code; for a quick summary, say
    python3 plom-make-DNM-sheets.py --help
"""

import argparse
import datetime
import pymupdf as fitz
import segno
import io


def stamp_page(PDFpage=None, TL=None, TR=None, BR=None, BL=None, title=None):
    if PDFpage is not None:
        mypage = PDFpage
    else:
        newdoc = fitz.Document()
        _ = newdoc.insert_page(0, width=612, height=792)
        mypage = newdoc[0]

    xmin, ymin, xmax, ymax = mypage.rect
    # print(f"(xmin,ymin,xmax,ymax) = ({xmin},{ymin},{xmax},{ymax})")

    # Set the QR image size (side length w). Default PNG image is 21x21 pixels.
    stretch = 3
    w = 21 * stretch

    if TL is not None:
        QRTL = segno.make(TL, micro=False)
        TLstream = io.BytesIO()
        QRTL.save(TLstream, kind="png")

        mypage.insert_image(fitz.Rect(xmin, ymin, xmin + w, ymin + w), stream=TLstream)

    if TR is not None:
        QRTR = segno.make(TR, micro=False)
        TRstream = io.BytesIO()
        QRTR.save(TRstream, kind="png")

        mypage.insert_image(fitz.Rect(xmax - w, ymin, xmax, ymin + w), stream=TRstream)

    if BR is not None:
        QRBR = segno.make(BR, micro=False)
        BRstream = io.BytesIO()
        QRBR.save(BRstream, kind="png")

        mypage.insert_image(fitz.Rect(xmax - w, ymax - w, xmax, ymax), stream=BRstream)

    if BL is not None:
        QRBL = segno.make(BL, micro=False)
        BLstream = io.BytesIO()
        QRBL.save(BLstream, kind="png")

        mypage.insert_image(fitz.Rect(xmin, ymax - w, xmin + w, ymax), stream=BLstream)

    if title is not None:
        # Centre title between QR boxes
        tlen = fitz.get_text_length(title)
        mypage.insert_text([(xmin + xmax) / 2 - tlen / 2, ymin + w / 2], title)
        # print(f"Sorry, adding title {title} is not implemented yet.")

    return mypage


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
    help="number of copies for given PDF, else number of physical sheets (optional)",
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
    help="Text to stamp at the top centre of each page (optional; default provided)",
)
parser.add_argument(
    "--course",
    type=str,
    default="PLOM",
    help="Alphanumeric course code to embed in QR codes (optional; default PLOM)",
)
parser.add_argument(
    "-O",
    "--outfile",
    type=str,
    default="PLOM-DNW.pdf",
    help="filename for output (optional, default DNM.pdf)",
)
parser.add_argument(
    "-d",
    "--debug",
    # nargs=0,
    action="store_true",
    default=False,
    help="enable debug printing",
)

if __name__ == "__main__":
    args = parser.parse_args()

    if args.debug:
        print(f"Starting {__file__} with these arguments:")
        print(args)

    timenow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    QRbase = args.course + ":"

    # Build a base document to decorate.
    # This must have a positive, even number of pages
    if args.pdf is not None:
        unstamped = fitz.Document(args.pdf)
    else:
        unstamped = fitz.Document()

    while len(unstamped) % 2 != 0 or len(unstamped) == 0:
        _ = unstamped.new_page(0, width=612, height=792)

    if args.debug:
        print(f"Unstamped template doc  is ready, with {len(unstamped)} pages.")

    outdoc = fitz.Document()
    for i in range(args.copies):
        QRmessage = QRbase + f"{i:04d}"
        for p in range(len(unstamped)):
            outdoc.insert_pdf(unstamped, from_page=p, to_page=p)
            ndx = len(outdoc) - 1
            stamp_page(
                outdoc[ndx],
                title=args.title,
                TL=f"DNM-TL\n{QRmessage}",
                TR=f"DNM-TR\n{QRmessage}",
                BL=f"DNM-BL\n{QRmessage}",
                BR=f"DNM-BR\n{QRmessage}",
            )

    if args.debug:
        print(f"Stamped output document is ready, with {len(outdoc)} pages.")

    outdoc.save(args.outfile)

    if args.debug:
        print(f"Wrote {len(outdoc)} pages to {args.outfile}. Done.")

    outdoc.close()
