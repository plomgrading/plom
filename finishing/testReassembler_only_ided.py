import os
import sys
import tempfile
from shutil import copyfile

sid = eval(sys.argv[1])
imgl = eval(sys.argv[2])

outname = "reassembled_ID_but_not_marked/test_{}.pdf".format(sid)

with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
    tfn = tf.name
    cmd = "convert -quality 100"
    for X in imgl[0:]:
        cmd += " {}".format(X)
    cmd += " {}".format(tfn)
    os.system(cmd)
    copyfile(tfn, outname)
