__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import glob
import sys
import os
import subprocess

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)
from ui_id_locator import Ui_idLocator


class IDLocator(QWidget):
    def __init__(self):
        super(IDLocator, self).__init__()

        # Set up the user interface from Designer.
        self.ui = Ui_idLocator()
        self.ui.setupUi(self)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)
        self.ui.imgLayout.addWidget(self.view)
        self.img = QPixmap()
        self.imgItem = QGraphicsPixmapItem(self.img)
        self.scene.addItem(self.imgItem)
        self.bottomRect = QGraphicsRectItem()
        self.brush = QBrush(QColor(0, 60, 80, 64))
        self.bottomRect.setBrush(self.brush)
        self.topRect = QGraphicsRectItem()
        self.brush = QBrush(QColor(60, 0, 80, 64))
        self.topRect.setBrush(self.brush)

        self.scene.addItem(self.bottomRect)
        self.scene.addItem(self.topRect)

        # Connect up the buttons.
        self.ui.goButton.clicked.connect(self.getToIt)
        self.ui.cancelButton.clicked.connect(self.close)
        self.grabFirstImage()
        self.setRectangles()

        self.ui.topSlider.valueChanged.connect(self.updateTopRect)
        self.ui.bottomSlider.valueChanged.connect(self.updateBottomRect)
        self.ui.topLayout.setAlignment(Qt.AlignHCenter)
        self.ui.bottomLayout.setAlignment(Qt.AlignHCenter)

    def grabFirstImage(self):
        fn = sorted(glob.glob("../scanAndGroup/readyForMarking/idgroup/*idg.png"))[0]
        print("Loading {}".format(fn))
        self.img = QPixmap(fn)
        self.imgItem.setPixmap(self.img)
        self.imgItem.setPos(0, 0)
        self.scene.setSceneRect(0, 0, self.img.width(), self.img.height())
        print(self.img.height(), self.img.width())
        self.scene.update()
        self.view.fitInView(self.imgItem, Qt.KeepAspectRatio)

    def setRectangles(self):
        w = self.img.width()
        h = self.img.height()
        self.updateTopRect()
        self.updateBottomRect()

    def updateTopRect(self):
        v = self.ui.topSlider.value() / 100
        w = self.img.width()
        h = self.img.height()
        self.topRect.setRect(0, 0, w, h * v)
        self.ui.topLabel.setText("{}".format(self.ui.topSlider.value()))

        if self.ui.topSlider.value() + self.ui.bottomSlider.value() > 100:
            self.ui.bottomSlider.setValue(100 - self.ui.topSlider.value())

    def updateBottomRect(self):
        v = self.ui.bottomSlider.value() / 100
        w = self.img.width()
        h = self.img.height()
        self.bottomRect.setRect(0, h * (1 - v), w, h * v)
        self.ui.bottomLabel.setText("{}".format(100 - self.ui.bottomSlider.value()))

        if self.ui.topSlider.value() + self.ui.bottomSlider.value() > 100:
            self.ui.topSlider.setValue(100 - self.ui.bottomSlider.value())

    def getToIt(self):
        h = self.img.height()
        t = int(max(0, self.ui.topSlider.value() - 5) / 100 * h)
        b = int(min(100, 105 - self.ui.bottomSlider.value()) / 100 * h)
        print("Run ID-code on image height range {} to {}".format(t, b))
        cmd = ["python3" "./readStudentID.py" str(t) str(b)]
        subprocess.check_call(cmd)
        self.close()


app = QApplication(sys.argv)
window = IDLocator()

window.show()
sys.exit(app.exec_())
