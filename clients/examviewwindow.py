import sys

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGridLayout, QPushButton, QWidget

class ExamViewWindow(QWidget):
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.view=ExamView(fname)
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

class ExamView(QGraphicsView):
    def __init__(self, fname):
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.scene=ExamScene()
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


class ExamScene(QGraphicsScene):
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
