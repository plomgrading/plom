import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QDialog, QGridLayout, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QGraphicsWidget, QLabel, QPushButton, QSpinBox

class ExamReorientWindow(QDialog):
    def __init__(self, fname):
        QGraphicsWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.fname=fname
        self.scene=QGraphicsScene();
        self.view=QGraphicsView(self.scene);

        self.image = QPixmap(self.fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.scene.addItem(self.imageItem)
        self.view.fitInView(self.imageItem,Qt.KeepAspectRatio)

        self.partL=QLabel("Number of pages")
        self.partSB=QSpinBox();
        self.partSB.setValue(1); self.partSB.setRange(1,9)

        self.splitB=QPushButton("Split")
        self.splitB.clicked.connect(lambda: self.splitIt())

        self.acceptB=QPushButton("Accept")
        self.acceptB.clicked.connect(lambda: self.acceptIt())

        self.cancelB=QPushButton("Cancel")
        self.cancelB.clicked.connect(lambda: self.reject())

        self.voidB = QPushButton(); self.voidB.setEnabled(False)

        self.grid = QGridLayout()

        self.grid.addWidget(self.partL,1,1)
        self.grid.addWidget(self.partSB,1,2)
        self.grid.addWidget(self.view,1,3,3,3)
        self.grid.addWidget(self.voidB,5,3,1,3)
        self.grid.addWidget(self.splitB,2,1,2,1)
        self.grid.addWidget(self.acceptB,10,2)
        self.grid.addWidget(self.cancelB,10,1)

        self.setLayout(self.grid)
        self.show()

    def splitIt(self):
        self.splitB.setEnabled(False)
        n = self.partSB.value()
        self.grid.removeWidget(self.view)
        self.grid.addWidget(self.view, 1,3,3,n)

        self.grid.removeWidget(self.voidB)

        self.flip={}
        for k in range(n):
            self.flip[k] = QPushButton("{}".format(k))
            self.flip[k].clicked.connect( lambda:self.flipPage() )
            self.grid.addWidget(self.flip[k],5,3+k)

        self.scene.removeItem(self.imageItem)
        w=self.image.width()//n; h=self.image.height()
        self.splitImg={}
        self.splitImgI={}
        for k in range(n):
            self.splitImg[k] = self.image.copy(w*k,0,w,h)
            self.splitImgI[k] = QGraphicsPixmapItem(self.splitImg[k])
            self.splitImgI[k].setPos(w*k,0)
            self.splitImgI[k].setTransformOriginPoint(w//2,h//2)
            self.scene.addItem(self.splitImgI[k])
        self.view.fitInView(0,0,w*n,h)

    def flipPage(self):
        sender=self.sender()
        k = int(sender.text().replace('&',''))
        if(self.splitImgI[k].rotation()==0):
            self.splitImgI[k].setRotation(180)
        else:
            self.splitImgI[k].setRotation(0)

    def acceptIt(self):
        w = self.image.width(); h=self.image.height()
        oimg = QPixmap(w,h)
        exporter = QPainter(oimg)
        self.scene.render(exporter)
        exporter.end()
        oimg.save(self.fname)
        self.accept()
