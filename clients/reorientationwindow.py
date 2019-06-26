__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsWidget,
    QLabel,
    QPushButton,
    QSpinBox,
)


class ExamReorientWindow(QDialog):
    """Widget to flip page images if they happen to be upsidedown.
    User selects how many pages in the group, the image is then
    split into that number of sub-images. They can then be flipped
    independently. The result is then saved.
    """

    def __init__(self, fname):
        QGraphicsWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        # Grab the image filename.
        self.fname = fname
        # Set up a QGraphicsScene and QGraphicsView
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        # Create a pixmap of the file and corresponding item
        self.image = QPixmap(self.fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        # Set scene dimensions to that of the image.
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        # Set the view to encompass the image.
        self.scene.addItem(self.imageItem)
        self.view.fitInView(self.imageItem, Qt.KeepAspectRatio)

        # Spinbox for entering the number of pages in the image
        self.partL = QLabel("Number of pages")
        self.partSB = QSpinBox()
        self.partSB.setValue(1)
        self.partSB.setRange(1, 9)

        # Buttons and connections to functions
        self.splitB = QPushButton("Split")
        self.splitB.clicked.connect(self.splitIt)
        self.acceptB = QPushButton("Accept")
        self.acceptB.clicked.connect(self.acceptIt)
        self.cancelB = QPushButton("Cancel")
        self.cancelB.clicked.connect(self.reject)
        # The void button will become a flip button for each page
        self.voidB = QPushButton()
        self.voidB.setEnabled(False)
        # lay out buttons etc
        self.grid = QGridLayout()
        self.grid.addWidget(self.partL, 1, 1)
        self.grid.addWidget(self.partSB, 1, 2)
        self.grid.addWidget(self.view, 1, 3, 3, 3)
        self.grid.addWidget(self.voidB, 5, 3, 1, 3)
        self.grid.addWidget(self.splitB, 2, 1, 2, 1)
        self.grid.addWidget(self.acceptB, 10, 2)
        self.grid.addWidget(self.cancelB, 10, 1)
        self.setLayout(self.grid)
        self.show()

    def splitIt(self):
        """Split the groupimage into user-selected number of pages
        and create individual page-flip buttons.
        """
        self.splitB.setEnabled(False)
        n = self.partSB.value()
        self.grid.removeWidget(self.view)
        self.grid.addWidget(self.view, 1, 3, 3, n)
        # remove the voidButton and replace with a button for each page.
        self.grid.removeWidget(self.voidB)
        self.flip = {}
        for k in range(n):
            self.flip[k] = QPushButton("{}".format(k))
            self.flip[k].clicked.connect(lambda: self.flipPage())
            self.grid.addWidget(self.flip[k], 5, 3 + k)
        # remove the original image and paste in each nth portion of it.
        self.scene.removeItem(self.imageItem)
        w = self.image.width() // n
        h = self.image.height()
        # Each split image and corresponding graphicsitem
        self.splitImg = {}
        self.splitImgI = {}
        for k in range(n):
            self.splitImg[k] = self.image.copy(w * k, 0, w, h)
            self.splitImgI[k] = QGraphicsPixmapItem(self.splitImg[k])
            self.splitImgI[k].setPos(w * k, 0)
            # Flip around centre.
            self.splitImgI[k].setTransformOriginPoint(w // 2, h // 2)
            # Place into the scene
            self.scene.addItem(self.splitImgI[k])
        self.view.fitInView(0, 0, w * n, h)

    def flipPage(self):
        # rotate the relevant nth of the groupimage by 180 around its centre
        sender = self.sender()
        k = int(sender.text().replace("&", ""))
        if self.splitImgI[k].rotation() == 0:
            self.splitImgI[k].setRotation(180)
        else:
            self.splitImgI[k].setRotation(0)

    def acceptIt(self):
        # Accept the result and save.
        w = self.image.width()
        h = self.image.height()
        # create pixmap of scene and painter to render it.
        oimg = QPixmap(w, h)
        exporter = QPainter(oimg)
        self.scene.render(exporter)
        exporter.end()
        # save result to file.
        oimg.save(self.fname)
        self.accept()
