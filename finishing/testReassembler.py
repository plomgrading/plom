import os
import sys
import fitz
import tempfile

sid = eval(sys.argv[1])
imgl = eval(sys.argv[2])

outname = "reassembled/test_{}.pdf".format(sid)

with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
    tfn = tf.name
    cmd = "convert -quality 100"
    for X in imgl[1:]:
        cmd += " {}".format(X)
    cmd += " {}".format(tfn)
    os.system(cmd)

    exam = fitz.open(tfn)
    cover = fitz.open(imgl[0])
    exam.insertPDF(cover, from_page=0, to_page=0, start_at=0)
    exam.save(outname)
