import fitz
import os
import sys
import tempfile
# takes StudentID and list of group image files as args.
# 0th item on list is the coverpage.
# other items are the groupimage files.
sid = eval(sys.argv[1])
imgl = eval(sys.argv[2])
# output as test_<StudentID>.pdf
outname = "reassembled/test_{}.pdf".format(sid)
# work on a tempfile
with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
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
    # save the output.
    exam.save(outname)
