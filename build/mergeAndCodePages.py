__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import sys
import os
import fitz
import pyqrcode
import tempfile

# this allows us to import from ../resources
sys.path.append("..")
from resources.tpv_utils import encodeTPV


# Take command line parameters
# 1 = name
# 2 = code
# 3 = length (ie number of pages)
# 4 = number of versions
# 5 = the test test number
# 6 = list of the version number for each page
name = sys.argv[1]
code = sys.argv[2]
length = int(sys.argv[3])
versions = int(sys.argv[4])
test = int(sys.argv[5])
pageVersions = eval(sys.argv[6])

# Command line parameters to imagemagick's mogrify
# puts a frame around the image.
mogParams = ' -mattecolor black -frame 1x1 -background "#FFFFFF" ' "-flatten"

# Which pdfsource file from which to extract each page version
V = {}
for v in range(1, versions + 1):
    V[v] = fitz.open("sourceVersions/version{}.pdf".format(v))

# Create test pdf as "exam"
exam = fitz.open()
# Insert the relevant page-versions into this pdf.
for p in range(1, length + 1):
    # Pymupdf starts pagecounts from 0 rather than 1. So offset things.
    exam.insertPDF(V[pageVersions[str(p)]], from_page=p - 1, to_page=p - 1, start_at=-1)

# Start to decorate the pages with qr-codes etc
# Get page width and height
pW = exam[0].bound().width
pH = exam[0].bound().height
# create a box for the test number near top-centre
rTC = fitz.Rect(pW // 2 - 50, 20, pW // 2 + 50, 40)
# put marks at top left/right so students don't write near
# staple or near where client will stamp marks
# create two "do not write" rectangles accordingly
rDNW0 = fitz.Rect(15, 15, 90, 90)
rDNW1 = fitz.Rect(pW - 90, 15, pW - 15, 90)
# 70x70 page-corner boxes for the QR codes
rNW = fitz.Rect(15, 20, 85, 90)
rNE = fitz.Rect(pW - 85, 20, pW - 15, 90)
rSW = fitz.Rect(15, pH - 90, 85, pH - 20)
rSE = fitz.Rect(pW - 85, pH - 90, pW - 15, pH - 20)

# Build all relevant pngs in a temp directory
with tempfile.TemporaryDirectory() as tmpDir:
    # filenames for testname QR and dnw rectangles
    nameFile = os.path.join(tmpDir, "name.png")
    dnw0File = os.path.join(tmpDir, "dnw0.png")
    dnw1File = os.path.join(tmpDir, "dnw1.png")
    # make a little grey triangle with the test name
    # put this in corner where staple is
    cmd = (
        'convert -size 116x58 xc:white -draw "stroke black fill grey '
        "path 'M 57,0  L 0,57  L 114,57 L 57,0 Z'\"  -gravity south "
        "-annotate +0+4 '{}' -rotate -45 -trim {}".format(name, dnw0File)
    )
    os.system(cmd)
    # and one for the other corner (back of page) in other orientation
    cmd = (
        'convert -size 116x58 xc:white -draw "stroke black fill grey '
        "path 'M 57,0  L 0,57  L 114,57 L 57,0 Z'\"  -gravity south "
        "-annotate +0+4 '{}' -rotate +45 -trim {}".format(name, dnw1File)
    )
    os.system(cmd)

    # create QR codes and other stamps for each test/page/version
    qrFile = {}
    tpFile = {}
    for p in range(1, length + 1):
        # 4 qr codes for the corners (one will be omitted for the staple)
        qrFile[p] = {}
        for i in range(1, 5):
            tpv = encodeTPV(test, p, pageVersions[str(p)], i, code)
            qr = pyqrcode.create(tpv, error="H")
            # save it in the associated file
            qrFile[p][i] = os.path.join(tmpDir, "page{}_{}.png".format(p, i))
            qr.png(qrFile[p][i], scale=4)
            # put a border around it
            os.system("mogrify {} {}".format(mogParams, qrFile[p][i]))

        # a file for the test/page stamp in top-centre of page
        tpFile[p] = os.path.join(
            tmpDir, "t{}p{}.png".format(str(test).zfill(4), str(p).zfill(2))
        )
        # create the test/page stamp using imagemagick
        os.system(
            "convert -pointsize 36 -size 200x42 caption:'{}.{}' -trim "
            "-gravity Center -extent 200x42 -bordercolor black "
            "-border 1 {}".format(str(test).zfill(4), str(p).zfill(2), tpFile[p])
        )
    # After creating all of the QRcodes etc we can put them onto
    # the actual pdf pages as pixmaps using pymupdf
    # read the DNW triangles in to pymupdf
    dnw0 = fitz.Pixmap(dnw0File)
    dnw1 = fitz.Pixmap(dnw1File)
    for p in range(length):
        # read in the test/page stamp
        testnumber = fitz.Pixmap(tpFile[p + 1])
        # put it at centre top each page
        exam[p].insertImage(rTC, pixmap=testnumber, overlay=True, keep_proportion=False)
        # grab the tpv QRcodes for current page
        qr = {}
        for i in range(1, 5):
            qr[i] = fitz.Pixmap(qrFile[p + 1][i])
        if p % 2 == 0:
            # if even page then stamp DNW near staple
            exam[p].insertImage(rDNW0, pixmap=dnw0, overlay=True)
            exam[p].insertImage(rNE, pixmap=qr[1], overlay=True)
            exam[p].insertImage(rSE, pixmap=qr[4], overlay=True)
            exam[p].insertImage(rSW, pixmap=qr[3], overlay=True)
        else:
            # odd page - put DNW stamp near staple
            exam[p].insertImage(rDNW1, pixmap=dnw1, overlay=True)
            exam[p].insertImage(rNW, pixmap=qr[2], overlay=True)
            exam[p].insertImage(rSW, pixmap=qr[3], overlay=True)
            exam[p].insertImage(rSE, pixmap=qr[4], overlay=True)

# Finally save the resulting pdf.
# Add the deflate option to compress the embedded pngs
# see https://pymupdf.readthedocs.io/en/latest/document/#Document.save
exam.save("examsToPrint/exam_{}.pdf".format(str(test).zfill(4)), deflate=True)
