# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QBrush, QColor, QGuiApplication, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QFormLayout,
    QGraphicsRectItem,
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# TODO: client references to be avoided, refactor to common utils?
from plom.client.useful_classes import ErrorMessage


class SelectRectangleWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames):
        QWidget.__init__(self)
        self.parent = parent

        if type(fnames) == list:
            self.initUI(fnames)
        else:
            self.initUI([fnames])
        self.rectangle = None
        self.whichFile = 0
        self.tool = "zoom"

    def initUI(self, fnames):
        self.setWindowTitle("Select ID Rectangle")
        self.vTW = QTabWidget()
        self.views = {}
        v = 0
        for fn in fnames:
            self.views[v] = IDView(self, [fn])
            self.views[v].setRenderHint(QPainter.HighQualityAntialiasing)
            self.vTW.addTab(self.views[v], "{}".format(v + 1))
            v += 1

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")
        self.zoomB = QPushButton("zoom tool")
        self.rectB = QPushButton("rectangle")
        self.delRectB = QPushButton("delete rectangle")
        self.acceptB = QPushButton("&accept")
        self.cancelB = QPushButton("&cancel")
        self.maxNormB = QPushButton("&max/norm")

        self.cancelB.clicked.connect(self.reject)
        self.acceptB.clicked.connect(self.check_and_accept_rect)
        # self.resetB.clicked.connect(lambda: self.view.resetView())
        self.maxNormB.clicked.connect(self.swapMaxNorm)
        self.zoomB.clicked.connect(self.zoomTool)
        self.rectB.clicked.connect(self.rectTool)
        self.delRectB.clicked.connect(self.deleteRect)

        self.resetB.setAutoDefault(False)  # return wont click the button by default.

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.vTW, 1, 1, 10, 6)
        grid.addWidget(self.zoomB, 6, 20)
        grid.addWidget(self.rectB, 5, 20)
        grid.addWidget(self.delRectB, 7, 20)
        grid.addWidget(self.resetB, 20, 1)
        grid.addWidget(self.cancelB, 20, 20)
        grid.addWidget(self.acceptB, 19, 20)
        grid.addWidget(self.maxNormB, 1, 20)
        self.setLayout(grid)
        self.show()

        self.rectB.animateClick()

    def check_and_accept_rect(self):
        """Checks and accepts only if there is a valid rectangle."""
        if self.rectangle is None:
            # if the user has selected a valid rectangle then we accept it, otherwise do we throw this warning.
            ErrorMessage("Error: no rectangle selected.").exec_()
            pass
        else:
            self.accept()

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def zoomTool(self):
        self.zoomB.setStyleSheet(
            "border: 2px solid #00aaaa; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop: 0 #00dddd, stop: 1 #00aaaa);"
        )
        self.rectB.setStyleSheet("")
        self.tool = "zoom"

    def rectTool(self):
        self.rectB.setStyleSheet(
            "border: 2px solid #00aaaa; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop: 0 #00dddd, stop: 1 #00aaaa);"
        )
        self.zoomB.setStyleSheet("")
        self.tool = "rect"

    def deleteRect(self):
        cv = self.vTW.currentIndex()
        self.views[cv].deleteRect()


class IDView(QGraphicsView):
    """Simple extension of QGraphicsView
    - containing an image and click-to-zoom/unzoom
    """

    def __init__(self, parent, fnames):
        QGraphicsView.__init__(self)
        self.parent = parent
        self.initUI(fnames)

    def initUI(self, fnames):
        # Make QGraphicsScene
        self.scene = QGraphicsScene()
        # TODO = handle different image sizes.
        self.images = {}
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImage(fnames)
        self.setBackgroundBrush(QBrush(Qt.darkCyan))
        self.parent.tool = "zoom"

        self.boxFlag = False
        self.originPos = QPointF(0, 0)
        self.currentPos = self.originPos
        self.boxItem = QGraphicsRectItem()
        self.boxItem.setPen(QPen(Qt.darkCyan, 1))
        self.boxItem.setBrush(QBrush(QColor(0, 255, 0, 64)))

    def updateImage(self, fnames):
        """Update the image with that from filename"""
        for n in self.images:
            self.imageGItem.removeFromGroup(self.images[n])
            self.images[n].setVisible(False)
        if fnames is not None:
            x = 0
            n = 0
            for fn in fnames:
                self.images[n] = QGraphicsPixmapItem(QPixmap(fn))
                self.images[n].setTransformationMode(Qt.SmoothTransformation)
                self.images[n].setPos(x, 0)
                self.images[n].setVisible(True)
                self.scene.addItem(self.images[n])
                x += self.images[n].boundingRect().width() + 10
                self.imageGItem.addToGroup(self.images[n])
                n += 1

        # Set sensible sizes and put into the view, and fit view to the image.
        br = self.imageGItem.boundingRect()
        self.scene.setSceneRect(
            0,
            0,
            max(1000, br.width()),
            max(1000, br.height()),
        )
        self.setScene(self.scene)
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)

    def deleteRect(self):
        if self.boxItem.scene() is None:
            return
        self.scene.removeItem(self.boxItem)
        self.parent.rectangle = None

    def mousePressEvent(self, event):
        if self.parent.tool == "rect":
            self.originPos = self.mapToScene(event.pos())
            self.currentPos = self.originPos
            self.boxItem.setRect(QRectF(self.originPos, self.currentPos))
            if self.boxItem.scene() is None:
                self.scene.addItem(self.boxItem)
            self.boxFlag = True
        else:
            super(IDView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent.tool == "rect" and self.boxFlag:
            self.currentPos = self.mapToScene(event.pos())
            if self.boxItem is None:
                return
            else:
                self.boxItem.setRect(QRectF(self.originPos, self.currentPos))
        else:
            super(IDView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.boxFlag:
            self.boxFlag = False
            self.parent.rectangle = self.boxItem.rect()
            self.parent.whichFile = self.parent.vTW.currentIndex()
            return

        """Left/right click to zoom in and out"""
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.scale(0.8, 0.8)
        else:
            self.scale(1.25, 1.25)
        self.centerOn(event.pos())

    def resetView(self):
        """Reset the view to its reasonable initial state."""
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)


class IDViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, sid):
        QWidget.__init__(self)
        self.parent = parent
        self.sid = sid

        if type(fnames) == list:
            self.initUI(fnames)
        else:
            self.initUI([fnames])

    def initUI(self, fnames):
        self.view = IDView(self, fnames)
        # Render nicely
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")

        self.acceptB = QPushButton("&close")
        self.maxNormB = QPushButton("&max/norm")

        self.acceptB.clicked.connect(self.accept)

        self.maxNormB.clicked.connect(self.swapMaxNorm)
        self.resetB.setAutoDefault(False)  # return wont click the button by default.

        self.idL = QLabel("ID: {}".format(self.sid))
        fnt = self.idL.font()
        fnt.setPointSize(fnt.pointSize() * 2)
        self.idL.setFont(fnt)

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.idL, 1, 1, 1, 6)
        grid.addWidget(self.view, 2, 1, 10, 6)
        grid.addWidget(self.acceptB, 19, 20)
        grid.addWidget(self.maxNormB, 1, 20)
        self.setLayout(grid)
        self.show()
        # Store the current exam view as a qtransform
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()

    def updateImage(self, fnames):
        """Pass file to the view to update the image"""
        # first store the current view transform and scroll values
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()
        # update the image
        if type(fnames) == list:
            self.view.updateImage(fnames)
        else:
            self.view.updateImage([fnames])

        # re-set the view transform and scroll values
        self.view.setTransform(self.viewTrans)
        self.view.horizontalScrollBar().setValue(self.dx)
        self.view.verticalScrollBar().setValue(self.dy)

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)
