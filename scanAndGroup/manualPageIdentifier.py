from collections import defaultdict
import glob
import json
import os
import sys

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QDialog, QErrorMessage, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QWidget

sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification

spec = TestSpecification()
examsProduced = {}
examsScanned = {}

def readExamsProduced():
    global examsProduced
    with open('../resources/examsProduced.json') as data_file:
        examsProduced = json.load(data_file)

def readExamsScanned():
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open('../resources/examsScanned.json') as data_file:
            examsScanned = json.load(data_file)

def writeExamsScanned():
    es = open("../resources/examsScanned.json", 'w')
    es.write(json.dumps(examsScanned, indent=2, sort_keys=True))
    es.close()

class PageViewWindow(QWidget):
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.view = PageView(fname)
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)

        self.resetB = QPushButton('reset view')
        self.resetB.clicked.connect(lambda: self.view.resetView() )

        grid = QGridLayout()
        grid.addWidget(self.view,1, 1, 10, 4)
        grid.addWidget(self.resetB, 20, 1)

        self.setLayout(grid)
        self.show()

    def updateImage(self, fname):
        self.view.updateImage(fname)

class PageView(QGraphicsView):
    def __init__(self, fname):
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.scene = PageScene()
        self.image = QPixmap(fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(0, 0, max(1000, self.image.width()), max(1000, self.image.height()))

        self.scene.addItem(self.imageItem)

        self.setScene(self.scene)
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def updateImage(self, fname):
        self.image = QPixmap(fname)
        self.imageItem.setPixmap(self.image)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.scale(0.8,0.8)
        else:
            self.scale(1.25,1.25)
        self.centerOn(event.pos())

    def resetView(self):
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def keyPressEvent(self, event):
        key = event.key()
        if(key == Qt.Key_Return or key == Qt.Key_Enter):
            self.parent().parent().identifyIt()
        else:
            super(PageView, self).keyPressEvent(event)

class PageScene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        self.ink = QPen(QColor(0, 255, 0), 2)
        self.lightBrush = QBrush(QColor(0, 255, 0, 16))
        self.boxItem = QGraphicsRectItem()

class ImageTable(QTableWidget):
    def __init__(self):
        super(ImageTable, self).__init__()
        self.setMinimumWidth(300)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.imageList = []
        self.reloadImageList()


    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.parent().identifyIt()
        else:
            super(ImageTable, self).keyPressEvent(event)

    def reloadImageList(self):
        self.imageList = []
        for fname in glob.glob("pageImages/problemImages/*.png"):
            self.imageList.append(fname)

    def populateTable(self):
        self.clear()
        self.setRowCount(len(self.imageList))
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(['file', 't', 'p', 'v', 'name'])
        for r in range(len(self.imageList)):
            fItem = QTableWidgetItem(os.path.basename(self.imageList[r]))
            tItem = QTableWidgetItem(".")
            pItem = QTableWidgetItem(".")
            vItem = QTableWidgetItem(".")
            nItem = QTableWidgetItem("?")
            self.setItem(r, 0, fItem)
            self.setItem(r, 1, tItem)
            self.setItem(r, 2, pItem)
            self.setItem(r, 3, vItem)
            self.setItem(r, 4, nItem)

        self.resizeColumnsToContents()
        self.selectRow(0)

    def setTPV(self, t, p, v):
        r = self.currentRow()
        self.item(r, 1).setText(t)
        self.item(r, 2).setText(p)
        self.item(r, 3).setText(v)
        self.item(r, 4).setText("Valid")
        self.resizeColumnsToContents()

    def setTGExtra(self, t, g):
        r = self.currentRow()
        self.item(r, 1).setText(t)
        self.item(r, 2).setText(g)
        # Determine version from test number and group number
        # v = examsProduced[t][p]  but p=page, not group
        # set p to be the spec.PageGroups[g][0] (ie first page of the group)
        self.item(r, 3).setText( examsProduced[t][spec.PageGroups[g]] )
        self.item(r, 4).setText("Extra")
        self.resizeColumnsToContents()

    def flipCurrent(self):
        r = self.currentRow();
        if r is not None:
            os.system("mogrify -rotate 180 -compress lossless pageImages/problemImages/{}".format(self.item(r,0).text()))
        return(r)

    def saveValid(self):
        for r in range(self.rowCount()):
            if self.item(r, 4).text() == 'Valid':
                t = self.item(r, 1).text()
                p = self.item(r, 2).text()
                v = int(self.item(r, 3).text())
                fname = self.item(r, 0).text()
                tsi = str(int(t))
                psi = str(int(p))
                if tsi not in examsScanned.keys():
                    examsScanned.update({tsi:{}})
                if psi not in examsScanned[tsi].keys():
                    examsScanned[tsi].update({psi:[v,fname]})
                else:
                    examsScanned[tsi][psi] = [v, fname]
                print("Assigning file {} to t{}p{}v{}".format(fname, t,p,v))
                os.system("cp pageImages/problemImages/{} ./decodedPages/page_{}/version_{}/t{}p{}v{}.png\n".format(fname, str(p).zfill(2), str(v), str(t).zfill(4), str(p).zfill(2), str(v)))
                os.system("mv pageImages/problemImages/{}* ./pageImages/alreadyProcessed/".format(fname))

    def saveExtras(self):
        for r in range(self.rowCount()):
            if self.item(r, 4).text() == 'Extra':
                t = self.item(r, 1).text()
                g = self.item(r, 2).text()
                v = self.item(r, 3).text()
                n = 0
                fname = self.item(r, 0).text()
                # Since there can be more than 1 extra page for the same pagegroup
                ename = "extraPages/xt{}g{}v{}n{}.png".format(str(t).zfill(4), str(g).zfill(2), v, n)
                while os.path.exists(ename):
                    v = v+1 #file exists, add 1 to counter.
                    ename = "extraPages/xt{}g{}v{}n{}.png".format(str(t).zfill(4), str(g).zfill(2), v, n)

                os.system("cp pageImages/problemImages/{} ./{}\n".format(fname, ename))
                os.system("mv pageImages/problemImages/{}* ./pageImages/alreadyProcessed/".format(fname))


class PageIDDialog(QDialog):
    def __init__(self):
        super(PageIDDialog, self).__init__()
        self.setWindowTitle("Manual check")

        grid = QGridLayout()

        self.nameL = QLabel("Name:")
        self.nameLE = QLineEdit("{}".format(spec.Name))
        grid.addWidget(self.nameL, 1, 1)
        grid.addWidget(self.nameLE, 1, 2)

        self.testL = QLabel("Test number")
        self.testSB = QSpinBox()
        self.testSB.setRange(0, spec.Tests)
        self.testSB.setValue(1)
        grid.addWidget(self.testL, 2, 1)
        grid.addWidget(self.testSB, 2, 2)

        self.pageL = QLabel("Page number")
        self.pageSB = QSpinBox()
        self.pageSB.setRange(0, spec.Length)
        self.pageSB.setValue(1)
        grid.addWidget(self.pageL, 3, 1)
        grid.addWidget(self.pageSB, 3, 2)

        self.versionL = QLabel("Version number")
        self.versionSB = QSpinBox()
        self.versionSB.setRange(0, spec.Versions)
        self.versionSB.setValue(1)
        grid.addWidget(self.versionL, 4, 1)
        grid.addWidget(self.versionSB, 4, 2)

        self.validateB = QPushButton("Validate")
        grid.addWidget(self.validateB, 5, 1)
        self.validateB.clicked.connect(self.validate)

        self.setLayout(grid)
        self.setModal(False)

    def validate(self):
        if self.checkIsValid():
            self.accept()
        else:
            self.reject()

    def checkIsValid(self):
        t = str(self.testSB.value())
        p = str(self.pageSB.value())
        v = self.versionSB.value()

        if examsProduced[t][p] != v:
            msg = QErrorMessage(self)
            msg.showMessage("TPV should be ({},{},{})".format(t, p, examsProduced[t][p]))
            msg.exec_()

            self.versionSB.setValue(0)
            return False


        if self.nameLE.text() != spec.Name:
            msg = QErrorMessage(self)
            msg.showMessage("Name should be \"{}\"".format(spec.Name))
            msg.exec_()
            return False

        if t in examsScanned:
            if p in examsScanned[t]:
                msg = QErrorMessage(self)
                msg.showMessage("TPV=({},{},{}) has already been scanned as file {}".format(t, p, examsScanned[t][p][0], examsScanned[t][p][1]))
                msg.exec_()
                self.versionSB.setValue(0)
                return False

        return True


class PageExtraDialog(QDialog):
    def __init__(self):
        super(PageExtraDialog, self).__init__()
        self.setWindowTitle("Extra page")

        grid = QGridLayout()

        self.testL = QLabel("Test number")
        self.testSB = QSpinBox()
        self.testSB.setRange(0, spec.Tests)
        self.testSB.setValue(1)
        grid.addWidget(self.testL, 1, 1)
        grid.addWidget(self.testSB, 1, 2)

        self.groupL = QLabel("Pagegroup number")
        self.groupSB = QSpinBox()
        self.groupSB.setRange(1, spec.getNumberOfGroups())
        self.groupSB.setValue(1)
        grid.addWidget(self.groupL, 2, 1)
        grid.addWidget(self.groupSB, 2, 2)

        self.validateB = QPushButton("Accept")
        grid.addWidget(self.validateB, 3, 1)
        self.validateB.clicked.connect(self.validate)

        self.setLayout(grid)
        self.setModal(False)

    def validate(self):
        if self.checkIsValid():
            self.accept()
        else:
            self.reject()

    def checkIsValid(self):
        t = str(self.testSB.value())
        g = str(self.groupSB.value())

        return True


class PageIdentifier(QWidget):
    def __init__(self):
        super(PageIdentifier, self).__init__()
        self.initUI()

    def selChanged(self, selnew, selold):
        self.pageImg.updateImage(self.imageT.imageList[selnew.indexes()[0].row()])

    def initUI(self):
        grid = QGridLayout()

        self.imageT = ImageTable()
        grid.addWidget(self.imageT, 1, 1, 4, 3)
        self.imageT.selectionModel().selectionChanged.connect(self.selChanged)

        self.pageImg = PageViewWindow()
        grid.addWidget(self.pageImg, 1, 4, 10, 10)
        self.imageT.populateTable()
        if self.imageT.imageList:
            self.pageImg.updateImage(self.imageT.imageList[0])

        self.extraB = QPushButton("Extra page")
        self.extraB.clicked.connect(self.extraPage)
        grid.addWidget(self.extraB,5,1)


        self.flippitB = QPushButton("Flip image")
        self.flippitB.clicked.connect(self.flipCurrent)
        grid.addWidget(self.flippitB,6,1)

        self.closeB = QPushButton("Save && Close")
        self.closeB.clicked.connect(self.saveValid)
        self.closeB.clicked.connect(self.saveExtras)
        grid.addWidget(self.closeB,8,1,2,2)

        self.closeB = QPushButton("Close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB,100,1)

        self.setLayout(grid)
        self.setWindowTitle('Identify Page Images')
        self.show()

    def saveValid(self):
        self.imageT.saveValid()
        writeExamsScanned()
        self.close()


    def extraPage(self):
        pexd = PageExtraDialog()
        if pexd.exec_() == QDialog.Accepted:
            t = str(pexd.testSB.value()).zfill(4)
            g = str(pexd.groupSB.value()).zfill(2)
            self.imageT.setTGExtra(t, g)
            self.imageT.setFocus()

    def flipCurrent(self):
        r = self.imageT.flipCurrent()
        if r is not None:
            self.pageImg.updateImage(self.imageT.imageList[r])

    def identifyIt(self):
        pidd = PageIDDialog()
        if pidd.exec_() == QDialog.Accepted:
            t = str(pidd.testSB.value()).zfill(4)
            p = str(pidd.pageSB.value()).zfill(2)
            v = str(pidd.versionSB.value())
            self.imageT.setTPV(t, p, v)
            self.imageT.setFocus()

def main():
    spec.readSpec()
    readExamsProduced()
    readExamsScanned()
    app = QApplication(sys.argv)
    PI = PageIdentifier()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
