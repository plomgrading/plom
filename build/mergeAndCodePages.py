import sys
import os
import fitz
import pyqrcode
import tempfile

smallQR = True

name = sys.argv[1]
length = int(sys.argv[2])
versions = int(sys.argv[3])
test = sys.argv[4].zfill(4)
pageVersions = eval(sys.argv[5])

mogOpA = "-gravity south -splice 0x16 -undercolor white -fill black -pointsize 16 -annotate +0+10"
mogOpB = "-bordercolor none -border 0x0 -mattecolor black -frame 1x1 -background \"#FFFFFF\" -flatten -rotate 270"
mogOpC = " -mattecolor black -frame 1x1 -background \"#FFFFFF\" -flatten -rotate 270"

V={}
for v in range(1, versions+1):
    V[v] = fitz.open("sourceVersions/version{}.pdf".format(v))

exam = fitz.open()
for p in range(1, length+1):
    # Pymupdf starts pagecounts from 0 rather than 1. So offset things.
    exam.insertPDF(V[pageVersions[str(p)]], from_page=p-1, to_page=p-1, start_at=-1)

# Fit the QRcodes inside boxes 112x100 or in 92x80 boxes
pW = exam[0].bound().width
pH = exam[0].bound().height
rTC = fitz.Rect(pW//2-50, 20, pW//2+50, 40) #a box for test number
rDNW = fitz.Rect(10, 10, 120, 40) #leave top-left of pages blank so that marks don't overwrite student work
rDNW0 = fitz.Rect(15, 15, 90, 90) #leave top-left of pages blank so that marks don't overwrite student work

# 70x70 boxes
rNW = fitz.Rect(15, 20, 85, 90)
rNE = fitz.Rect(pW-85, 20, pW-15, 90)
rSW = fitz.Rect(15, pH-90, 85, pH-20)
rSE = fitz.Rect(pW-85, pH-90, pW-15, pH-20)

with tempfile.TemporaryDirectory() as tmpDir:
    nameQR = pyqrcode.create('N.{}'.format(name), error='H')
    nameFile = os.path.join(tmpDir, "name.png")
    dnwFile = os.path.join(tmpDir, "dnw.png")
    dnw0File = os.path.join(tmpDir, "dnw0.png")

    nameQR.png(nameFile, scale=4)
    os.system("mogrify {} {}".format(mogOpC, nameFile))

    os.system("convert -size 100x30 xc:grey -bordercolor black -border 1 {}".format(dnwFile))
    cmd = "convert -size 116x58 xc:white -draw \"stroke black fill grey path \'M 57,0  L 0,57  L 114,57 L 57,0 Z\'\"  -gravity south -annotate +0+4 \'{}\' -rotate -45 -trim {}".format(name, dnw0File)
    os.system(cmd)

    pageQRs = {}
    pageFile = {}
    tpFile={}
    for p in range(1, length+1):
        tpv = 't{}p{}v{}'.format(str(test).zfill(4), str(p).zfill(2), pageVersions[str(p)])
        pageQRs[p] = pyqrcode.create(tpv, error='H')
        pageFile[p] = os.path.join(tmpDir, "page{}.png".format(p))
        pageQRs[p].png(pageFile[p], scale=4)
        os.system("mogrify {} {}".format(mogOpC, pageFile[p]))
        tpFile[p] = os.path.join(tmpDir, "t{}p{}.png".format(str(test).zfill(4), str(p).zfill(2)))
        os.system("convert -pointsize 36 -size 200x42 caption:'{}.{}' -trim -gravity Center -extent 200x42 -bordercolor black -border 1 {}".format( str(test).zfill(4), str(p).zfill(2), tpFile[p]) )

    qrName = fitz.Pixmap(nameFile)
    dnw = fitz.Pixmap(dnwFile)
    dnw0 = fitz.Pixmap(dnw0File)
    for p in range(length):
        testnumber = fitz.Pixmap(tpFile[p+1])
        exam[p].insertImage(rTC, pixmap=testnumber, overlay=True) #put testnumber at centre top each page
        qrPage = fitz.Pixmap(pageFile[p+1])
        if p % 2 == 0:
            exam[p].insertImage(rNE, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rDNW0, pixmap=dnw0, overlay=True)
            exam[p].insertImage(rSE, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rSW, pixmap=qrName, overlay=True)
        else:
            exam[p].insertImage(rNW, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rSW, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rSE, pixmap=qrName, overlay=True)

exam.save("examsToPrint/exam_{}.pdf".format(str(test).zfill(4)))
