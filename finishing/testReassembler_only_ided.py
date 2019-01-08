__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

import os
import sys
import tempfile
import shutil

# takes StudentID and list of group image files as args.
sid = eval(sys.argv[1])
imgl = eval(sys.argv[2])
# output to indicate file
outname = "reassembled_ID_but_not_marked/test_{}.pdf".format(sid)
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
    # copy the tempfile into place.
    shutil.copyfile(tf.name, outname)
