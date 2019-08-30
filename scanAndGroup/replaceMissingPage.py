__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import sys
import os
import fitz
import tempfile

# Take command line parameters
# 1 = test
# 2 = page

test = sys.argv[1]
page = sys.argv[2]
tpImage = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
# create the test/page stamp using imagemagick
os.system(
    "convert -pointsize 36 -size 200x42 caption:'{}.{}' -trim "
    "-gravity Center -extent 200x42 -bordercolor black "
    "-border 1 {}".format(str(test).zfill(4), str(page).zfill(2), tpImage.name)
)

DNS = fitz.open("../resources/pageNotSubmitted.pdf")  # create a 'did not submit' pdf
# create a box for the test number near top-centre
# Get page width
pW = DNS[0].bound().width
rTC = fitz.Rect(pW // 2 - 50, 20, pW // 2 + 50, 40)
testnumber = fitz.Pixmap(tpImage.name)
DNS[0].insertImage(rTC, pixmap=testnumber, overlay=True, keep_proportion=False)

DNS.save("argh.pdf", garbage=4, deflate=True, clean=True)
