__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import fitz
import os
import sys
import tempfile

# takes testname, StudentID and list of group image files as args.
shortName = sys.argv[1]
sid = eval(sys.argv[2])
imgl = eval(sys.argv[3])
# output to indicate file
outname = "reassembled_ID_but_not_marked/{}_{}.pdf".format(shortName, sid)
# work on a tempfile
with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
    # use imagemagick to glob together the groupimages
    # build the command
    cmd = "convert -quality 100"
    for X in imgl[0:]:
        cmd += " {}".format(X)
    cmd += " {}".format(tf.name)
    # run the command
    os.system(cmd)
    # open with fitz/pymupdf and update the metadata
    exam = fitz.open(tf.name)
    # title of PDF is "<testname> <sid>"
    exam.setMetadata({"title": "{} {}".format(shortName, sid), "producer": "PLOM"})
    # save the output.
    exam.save(outname)
