__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import fitz
import os
import sys
import tempfile

# takes testname StudentID and list of group image files as args.
# 0th item on list is the coverpage.
# other items are the groupimage files.
shortName = sys.argv[1]
sid = eval(sys.argv[2])
imgl = eval(sys.argv[3])
# output as test_<StudentID>.pdf
# note we know the shortname is alphanumeric with no spaces
# so this is safe.
outname = "reassembled/{}_{}.pdf".format(shortName, sid)
# work on a tempfile
with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
    # use imagemagick to glob the group-images together into a pdf.
    # first build the imagemagick command.
    cmd = "convert -quality 100"
    for X in imgl[1:]:
        cmd += " {}".format(X)
    cmd += " {}".format(tf.name)
    # run the command.
    os.system(cmd)
    # Now attach the coverpage to the front using fitz / pymupdf
    exam = fitz.open(tf.name)
    # grab the coverpage
    cover = fitz.open(imgl[0])
    # insert the coverpage as the 0th page.
    exam.insertPDF(cover, from_page=0, to_page=0, start_at=0)
    # title of PDF is "<testname> <sid>"
    exam.setMetadata({"title": "{} {}".format(shortName, sid), "producer": "Plom"})
    # save the output.
    exam.save(outname)
