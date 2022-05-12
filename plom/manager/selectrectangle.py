# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021-2022 Colin B. Macdonald

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QImageReader,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QDialog,
    QGraphicsRectItem,
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QLabel,
    QPushButton,
)

from plom.client.useful_classes import WarnMsg


class SelectRectangleWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames):
        super().__init__(parent)

        if type(fnames) == list:
            self.initUI(fnames)
        else:
            self.initUI([fnames])
        self.rectangle = None
        self.tool = "zoom"

    def initUI(self, fnames):
        self.setWindowTitle("Select ID Rectangle")
        self.view = IDView(self, fnames)
        self.view.setRenderHint(QPainter.Antialiasing)

        self.resetB = QPushButton("reset view")
        self.zoomB = QPushButton("zoom tool")
        self.rectB = QPushButton("rectangle")
        self.delRectB = QPushButton("delete rectangle")
        self.acceptB = QPushButton("&accept")
        self.cancelB = QPushButton("&cancel")

        self.cancelB.clicked.connect(self.reject)
        self.acceptB.clicked.connect(self.check_and_accept_rect)
        self.resetB.clicked.connect(self.view.resetView)
        self.zoomB.clicked.connect(self.zoomTool)
        self.rectB.clicked.connect(self.rectTool)
        self.delRectB.clicked.connect(self.deleteRect)

        self.resetB.setAutoDefault(False)  # return won't click the button by default.

        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 6)
        help = QLabel(
            """
            <p>Draw a box around the IDBox template.</p>
            <ul>
              <li>Bigger is better: a few cm above and below.</li>
              <li>Only the top/bottom are currently used.</li>
              <li>Tool won't work if you didn't use the IDBox template.</li>
              <li>Tool does not fail gracefully: watch server log/stdout.</li>.
            </ul>
        """
        )
        help.setWordWrap(True)
        grid.addWidget(help, 1, 19, 4, 3)
        grid.addWidget(self.rectB, 5, 20)
        grid.addWidget(self.zoomB, 6, 20)
        grid.addWidget(self.delRectB, 7, 20)
        grid.addWidget(self.resetB, 20, 1)
        grid.addWidget(self.cancelB, 20, 20)
        grid.addWidget(self.acceptB, 20, 21)
        self.setLayout(grid)

        self.rectB.animateClick()

    def check_and_accept_rect(self):
        """Checks and accepts only if there is a valid rectangle."""
        if self.rectangle is None:
            # if the user has selected a valid rectangle then we accept it, otherwise do we throw this warning.
            WarnMsg(self, "Error: no rectangle selected.").exec()
            pass
        else:
            t = self.view.imageGItem.boundingRect().top()
            h = self.view.imageGItem.boundingRect().height() - t
            self.top_bottom_values = (
                max(0, (self.rectangle.top() - t) / h),
                min(1, (self.rectangle.bottom() - t) / h),
            )
            self.accept()

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
        self.view.deleteRect()


# TODO: maybe it can be a subclass of ExamView/ImageViewWidget?
class IDView(QGraphicsView):
    """Simple extension of QGraphicsView
    - containing an image and click-to-zoom/unzoom
    """

    def __init__(self, parent, fnames):
        # parenting this widget gives a postage-stamp-sized view, not sure why
        super().__init__()
        self._parent = parent
        self.scene = QGraphicsScene()
        # TODO = handle different image sizes.
        self.images = {}
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImages(fnames)
        self.setBackgroundBrush(QBrush(Qt.darkCyan))
        self._parent.tool = "zoom"

        self.boxFlag = False
        self.originPos = QPointF(0, 0)
        self.currentPos = self.originPos
        self.boxItem = QGraphicsRectItem()
        self.boxItem.setPen(QPen(Qt.darkCyan, 1))
        self.boxItem.setBrush(QBrush(QColor(0, 255, 0, 64)))

    def updateImages(self, fnames):
        """Update the image with that from filename"""
        if isinstance(fnames, str):
            fnames = [fnames]
        for n in self.images:
            self.imageGItem.removeFromGroup(self.images[n])
            self.images[n].setVisible(False)
        if fnames is not None:
            x = 0
            n = 0
            for fn in fnames:
                qir = QImageReader(str(fn))
                # deal with jpeg exif rotations
                qir.setAutoTransform(True)
                pix = QPixmap(qir.read())
                if pix.isNull():
                    raise RuntimeError(f"Could not read an image from {fn}")
                self.images[n] = QGraphicsPixmapItem(pix)
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
        self._parent.rectangle = None

    def mousePressEvent(self, event):
        if self._parent.tool == "rect":
            self.originPos = self.mapToScene(event.pos())
            self.currentPos = self.originPos
            self.boxItem.setRect(QRectF(self.originPos, self.currentPos))
            if self.boxItem.scene() is None:
                self.scene.addItem(self.boxItem)
            self.boxFlag = True
        else:
            super(IDView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._parent.tool == "rect" and self.boxFlag:
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
            self._parent.rectangle = self.boxItem.rect()
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
