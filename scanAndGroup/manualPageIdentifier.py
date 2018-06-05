import sys
import os
import glob

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGridLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QWidget

class PageViewWindow(QWidget):
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.view=PageView(fname)
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)

        self.resetB=QPushButton('reset view')
        self.resetB.clicked.connect(lambda: self.view.resetView() )

        grid = QGridLayout()
        grid.addWidget(self.view,1,1,10,4)
        grid.addWidget(self.resetB,20,1)

        self.setLayout(grid)
        self.show()

    def updateImage(self,fname):
        self.view.updateImage(fname)

class PageView(QGraphicsView):
    def __init__(self, fname):
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.scene=PageScene()
        self.image = QPixmap(fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(0, 0, max(1000,self.image.width()), max(1000,self.image.height()))

        self.scene.addItem(self.imageItem)

        self.setScene(self.scene)
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def updateImage(self,fname):
        self.image = QPixmap(fname)
        self.imageItem.setPixmap(self.image)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        rec=self.scene.boxItem.rect()
        if( rec.height()>=64 and rec.width()>=64 ):
            self.fitInView(self.scene.boxItem,Qt.KeepAspectRatio)
        self.scene.mouseReleaseEvent(event)

    def resetView(self):
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)


class PageScene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        self.ink = QPen(QColor(0,255,0),2)
        self.lightBrush = QBrush(QColor(0,255,0,16))

    def mousePressEvent(self, event):
        self.origin_pos = event.scenePos()
        self.current_pos = self.origin_pos
        self.boxItem = QGraphicsRectItem(QRectF(self.origin_pos, self.current_pos))
        self.boxItem.setPen(self.ink); self.boxItem.setBrush(self.lightBrush)
        self.addItem(self.boxItem)

    def mouseMoveEvent(self, event):
        self.current_pos = event.scenePos()
        self.boxItem.setRect(QRectF(self.origin_pos, self.current_pos))

    def mouseReleaseEvent(self, event):
        self.removeItem(self.boxItem)


class IDBox(QWidget):
    def __init__(self):
        super(IDBox, self).__init__()
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        self.testL = QLabel("t:")
        grid.addWidget(self.testL,1,1)
        self.pageL = QLabel("p:")
        grid.addWidget(self.pageL,2,1)
        self.versionL = QLabel("v:")
        grid.addWidget(self.versionL,3,1)
        self.nameL = QLabel("name:")
        grid.addWidget(self.nameL,4,1)
        self.setLayout(grid)

class PageIdentifier(QWidget):
    def __init__(self):
        super(PageIdentifier, self).__init__()
        self.imageList=[]
        self.reloadImageList()
        self.initUI()

    def reloadImageList(self):
        for fname in glob.glob("pageImages/problemImages/*.png"):
            self.imageList.append(fname)

    def populateTable(self):
        self.imageT.clear()
        self.imageT.setRowCount(len(self.imageList))
        self.imageT.setColumnCount(5)
        self.imageT.setHorizontalHeaderLabels(['file', 't', 'p', 'v', 'name'])
        for r in range( len(self.imageList) ):
            print("Adding image {} at row {}".format(self.imageList[r], r))
            fItem = QTableWidgetItem(os.path.basename(self.imageList[r]))
            tItem = QTableWidgetItem(".")
            pItem = QTableWidgetItem(".")
            vItem = QTableWidgetItem(".")
            nItem = QTableWidgetItem("?")
            self.imageT.setItem(r,0,fItem)
            self.imageT.setItem(r,1,tItem)
            self.imageT.setItem(r,2,pItem)
            self.imageT.setItem(r,3,vItem)
            self.imageT.setItem(r,4,nItem)

        self.imageT.resizeColumnsToContents()
        self.imageT.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.imageT.setSelectionMode(QAbstractItemView.SingleSelection)
        self.imageT.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.imageT.selectionModel().selectionChanged.connect(self.selChanged)

    def selChanged(self, selnew, selold):
        self.pageImg.updateImage( self.imageList[selnew.indexes()[0].row()] )

    def initUI(self):
      grid = QGridLayout()

      self.imageT = QTableWidget()
      self.populateTable()
      grid.addWidget(self.imageT,1,1,4,2)

      self.pageImg = PageViewWindow()
      grid.addWidget(self.pageImg, 1,3,10,10)

      self.idIt = IDBox()
      grid.addWidget(self.idIt, 5,1)

      self.closeB = QPushButton("Close")
      self.closeB.clicked.connect(self.close)
      grid.addWidget(self.closeB,100,1)

      self.setLayout(grid)
      self.setWindowTitle('Identify Page Images')
      self.show()


def main():
    app = QApplication(sys.argv)
    PI = PageIdentifier()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
