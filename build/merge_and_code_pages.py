import sys
import os
import fitz
import pyqrcode
import tempfile

name = sys.argv[1]
length = int(sys.argv[2])
versions = int(sys.argv[3])
test = sys.argv[4].zfill(4)
pageVersions = eval(sys.argv[5])
# print("Test name = {}".format(name))
# print("Test number = {}".format(test))
# print("pages = {}".format(pageVersions))

mogOpA = "-gravity south -splice 0x16 -undercolor white -fill black -pointsize 16 -annotate +0+10"
mogOpB = "-bordercolor none -border 0x0 -mattecolor black -frame 1x1 -background \"#FFFFFF\" -flatten -rotate 270"

V={}
for v in range(1,versions+1):
    V[v] = fitz.open("sourceVersions/version{}.pdf".format(v))

exam = fitz.open()
for p in range(1,length+1):
    # Very annoyingly pymupdf starts pagecounts from 0 rather than 1. So offset things.
    exam.insertPDF(V[pageVersions[p]], from_page=p-1, to_page=p-1, start_at=-1)

#Fit the QRcodes inside boxes 112x100
pW = exam[0].bound().width
pH = exam[0].bound().height
rNW = fitz.Rect(10,10,122,110)
rNE = fitz.Rect(pW-122,10,pW-10,110)
rSW = fitz.Rect(10,pH-110,122,pH-10)
rSE = fitz.Rect(pW-122,pH-110,pW-10,pH-10)

with tempfile.TemporaryDirectory() as tmpDir:
    nameQR = pyqrcode.create('N.{}'.format(name), error='H')
    nameFile=os.path.join(tmpDir,"name.png")
    nameQR.png(nameFile, scale=4)
    os.system("mogrify {} \"{}\" {} {}".format(mogOpA, name, mogOpB, nameFile))
    pageQRs = {}
    pageFile = {}
    for p in range(1,length+1):
        tpv = 't{}p{}v{}'.format(str(test).zfill(4), str(p).zfill(2), pageVersions[p])
        pageQRs[p] = pyqrcode.create(tpv, error='H')
        pageFile[p]=os.path.join(tmpDir,"page{}.png".format(p))
        pageQRs[p].png(pageFile[p], scale=4)
        os.system("mogrify {} \"{}\" {} {}".format(mogOpA, tpv, mogOpB, pageFile[p]))

    qrName = fitz.Pixmap(nameFile)
    for p in range(length):
        qrPage = fitz.Pixmap(pageFile[p+1])
        if(p%2==0):
            exam[p].insertImage(rNE, pixmap=qrPage, overlay=False)
            exam[p].insertImage(rSE, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rSW, pixmap=qrName, overlay=True)
        else:
            exam[p].insertImage(rNW, pixmap=qrPage, overlay=False)
            exam[p].insertImage(rSW, pixmap=qrPage, overlay=True)
            exam[p].insertImage(rSE, pixmap=qrName, overlay=True)

exam.save("examsToPrint/test_{}.pdf".format(str(test).zfill(4)))
