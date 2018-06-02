import os,json
from testspecification import TestSpecification
from collections import defaultdict

def readExamsGrouped():
    global examsGrouped
    if(os.path.exists("../resources/examsGrouped.json")):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)

def readExamsIDed():
    global examsIDed
    if(os.path.exists("../resources/examsIdentified.json")):
        with open('../resources/examsIdentified.json') as data_file:
            examsIDed = json.load(data_file)

def readGroupImagesMarked():
    global groupImagesMarked
    if(os.path.exists("../resources/groupImagesMarked.json")):
        with open('../resources/groupImagesMarked.json') as data_file:
            groupImagesMarked = json.load(data_file)

def checkMarked(n):
    if(n not in groupImagesMarked):
        print("\tTotally unmarked")
        return(False)
    flag=True
    for pg in range(1,spec.getNumberOfGroups()+1):
        pgs = str(pg)
        if( pgs in groupImagesMarked[n] ):
            v = groupImagesMarked[n][pgs][0]
            tgv = "G{}g{}v{}".format( n.zfill(4), str(pg).zfill(2),v)
            # print("\tPG image {}".format(tgv), end='')
            # print("\tpg{} v{} = {}".format(pg,v, groupImagesMarked[n][pgs][1]))
            # examScores[n].append([pg, v, groupImagesMarked[n][pgs][1]])
        else:
            # print("\tpg{} unmarked".format(pg))
            flag=False
    if(flag==False):
        print("\tPartially marked")
    return(flag)

def checkIDed(n):
    print("\tID image {}".format(examsGrouped[n][0]), end='')
    if(n not in examsIDed):
        print("\tNo ID")
        return(False)
    else:
        print("\tID = ", examsIDed[n][1:3])
        return(True)

def checkExam(n):
    global examsIDed
    global groupImagesMarked
    print("##################\nExam {}".format(n))
    if( checkIDed(n) and checkMarked(n) ):
        print("\tComplete - build front page and reassemble.")
        return(True)
    else:
        return(False)

def frontPage(n):
    os.chdir('frontPages')
    fh = open("exam_{}.tex".format(n.zfill(4)), 'w')
    fh.write('\\documentclass[12pt, letterpage]{article}\n\\pagestyle{empty}\n\\usepackage{palatino}\n')
    fh.write('\\begin{document}\n')
    fh.write('Student Number: {}\n\n'.format(examsIDed[n][1]))
    fh.write('Student Name: {}\n\n'.format(examsIDed[n][2]))
    fh.write('Exam number: {}\n\n'.format(n))
    fh.write('\\vspace{1cm}\n')

    tot = 0
    scr = 0
    fh.write('\\begin{tabular}{|l|r|r||r|}\n\\hline\n')
    fh.write('Page group & Mark & Out of & Version\\\\ \n \\hline\n')
    for pg in range(spec.getNumberOfGroups()):
        tot += spec.Marks[pg]
        scr += examScores[n][pg][2]
        fh.write('{} & {} & {} & {} \\\\ \n'.format(pg, examScores[n][pg][2], spec.Marks[pg], examScores[n][pg][1]))

    fh.write('\\hline \\hline \n')
    fh.write('Total & {} & {} & $\cdot$ \\\\ \n'.format(scr, tot))
    fh.write('\\hline \n')
    fh.write('\\end{tabular}\n')
    fh.write('\\end{document}\n')
    fh.close()
    os.system("pdflatex quiet exam_{}.tex".format(n.zfill(4)))
    os.system("gs -quiet -dNumRenderingThreads=4 -dNOPAUSE -sDEVICE=png256 -o exam_{}.png -r200 exam_{}.pdf".format(n.zfill(4),n.zfill(4)))
    os.chdir('../')

def reassembleExam(n):
    pdfl = "frontPages/exam_{}.png".format(n.zfill(4))
    pdfl += " ../scanAndGroup/readyForGrading/idgroup/{}.png".format(examsGrouped[n][0])
    for pg in range(spec.getNumberOfGroups()):
        pdfl += " ../imageServer/markedPapers/G{}.png".format(examsGrouped[n][pg+1][1:])
    cmd = 'img2pdf --colorspace RGBA -o reassembled/exam_{}.pdf {}'.format(n.zfill(4), pdfl)
    os.system(cmd)
    #optionally copy exam_n.pdf to exam_SID.pdf
    cmd = 'mv ./reassembled/exam_{}.pdf ./reassembled/exam_{}.pdf'.format(n.zfill(4),examsIDed[n][1])
    os.system(cmd)

def writeExamsCompleted():
    fh = open("../resources/examsCompleted.json",'w')
    fh.write( json.dumps(examsCompleted, indent=2, sort_keys=True))
    fh.close()


os.system('mkdir -p reassembled')
os.system('mkdir -p frontPages')

spec = TestSpecification()
spec.readSpec()

readExamsGrouped()
readExamsIDed()
examScores=defaultdict(list)
readGroupImagesMarked()

examsCompleted={}
for n in sorted(examsGrouped.keys()):
    examsCompleted[n]=checkExam(n)

writeExamsCompleted()
