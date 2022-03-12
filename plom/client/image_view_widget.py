# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtGui import QBrush, QImageReader, QPainter, QPixmap, QTransform
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from plom import ScenePixelHeight
from plom.client.backGrid import BackGrid


class ImageViewWidget(QWidget):
    """Simple view widget for pageimages to be embedded in other windows.

    args:
        parent (QWidget): the parent container for this widget.
        image_data (None/list[dict]/list[str/pathlib.Path]/str/pathlib.Path):
            each dict has keys 'filename' and 'orientation' (and
            possibly others).
            Currently every image is used and the list order
            determines the order.  That is subject to change.
            Can also be a list of `pathlib.Path` or `str` of image
            filenames.  Can also be a single `str`/`pathlib.Path`,
            for a single image.
            Unclear whether the caller must maintain
            these image files on disc or if the QPixmap will reads it once
            and stores it.  See Issue #1842.  For now, safest to assume
            you must maintain it.
        has_reset_button (bool): whether to include a reset zoom button,
            default: True.
        compact (bool): whether to include a margin (default True) or
            not.  Correct choice will depend on parent but is probably
            only cosmetic.
        dark_background (bool): sometimes its useful to have some
            higher-constrast matting around images.  Default: False.
    """

    def __init__(
        self,
        parent,
        image_data=None,
        *,
        has_reset_button=True,
        compact=True,
        dark_background=False,
    ):
        super().__init__(parent)
        # Grab an examview widget (a interactive subclass of QGraphicsView)
        self.view = ExamView(image_data, dark_background=dark_background)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        grid = QVBoxLayout()
        if compact:
            grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.view, 1)
        grid.setSpacing(3)
        self.zoomLockB = None
        if has_reset_button:
            resetB = QToolButton()
            # resetB.setText("\N{Leftwards Arrow To Bar Over Rightwards Arrow To Bar}")
            # resetB.setText("\N{Up Down Black Arrow}")
            resetB.setText("reset")
            resetB.setToolTip("reset zoom")
            resetB.clicked.connect(self.resetView)
            zoomInB = QToolButton()
            zoomInB.setText("\N{Heavy Plus Sign}")
            zoomInB.setToolTip("zoom in")
            zoomInB.clicked.connect(self.zoomIn)
            zoomOutB = QToolButton()
            zoomOutB.setText("\N{Heavy Minus Sign}")
            zoomOutB.setToolTip("zoom out")
            zoomOutB.clicked.connect(self.zoomOut)
            zoomLockB = QToolButton()
            zoomLockB.setText("\N{Lock}")
            zoomLockB.setCheckable(True)
            zoomLockB.setChecked(False)
            zoomLockB.clicked.connect(self.zoomLockToggle)
            self.zoomLockB = zoomLockB
            self._zoomLockUpdateTooltip()

            buttons = QHBoxLayout()
            buttons.setContentsMargins(0, 0, 0, 0)
            buttons.setSpacing(6)
            buttons.addStretch(1)
            buttons.addWidget(resetB)
            buttons.addWidget(zoomInB)
            buttons.addWidget(zoomOutB)
            buttons.addWidget(zoomLockB)
            buttons.addStretch(1)
            grid.addLayout(buttons)

        self.setLayout(grid)
        # Store the current exam view as a qtransform
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()

    def updateImage(self, image_data):
        """Pass file(s) to the view to update the image"""
        # first store the current view transform and scroll values
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()
        self.view.updateImages(image_data)

        # re-set the view transform and scroll values
        self.view.setTransform(self.viewTrans)
        self.view.horizontalScrollBar().setValue(self.dx)
        self.view.verticalScrollBar().setValue(self.dy)

    def resizeEvent(self, whatev):
        """Seems to ensure image gets resize on window resize."""
        if self.zoomLockB and self.zoomLockB.isChecked():
            return
        self.view.resetView()

    def resetView(self):
        if self.zoomLockB:
            self.zoomLockB.setChecked(False)
            self._zoomLockUpdateTooltip()
        self.view.resetView()

    def zoomIn(self):
        self.view.zoomIn()
        if self.zoomLockB:
            self.zoomLockB.setChecked(True)
            self._zoomLockUpdateTooltip()

    def zoomOut(self):
        self.view.zoomOut()
        if self.zoomLockB:
            self.zoomLockB.setChecked(True)
            self._zoomLockUpdateTooltip()

    def zoomLockToggle(self):
        self._zoomLockUpdateTooltip()

    def _zoomLockUpdateTooltip(self):
        if self.zoomLockB.isChecked():
            self.zoomLockB.setToolTip("zoom: locked")
        else:
            self.zoomLockB.setToolTip("zoom: fit on window resize")

    def forceRedrawOrSomeBullshit(self):
        """Horrid workaround when we cannot get proper redraws.

        Colin (and Andrew) will be very happy with this function is
        refactored away by a Qt expert.  Or even a Qt novice.  Anyone
        with a pulse really.

        This does not seem to crash if you close the dialog before the
        timer fires.  That's the only positive thing I can say about it.
        """
        QTimer.singleShot(32, self.view.resetView)


class ExamView(QGraphicsView):
    """Display images with some interaction: click-to-zoom/unzoom

    args:
        image_data (None/list[dict]/list[str/pathlib.Path]/str/pathlib.Path):
            each dict has keys 'filename' and 'orientation' (and
            possibly others).
            Currently every image is used and the list order
            determines the order.  That is subject to change.
            Can also be a list of `pathlib.Path` or `str` of image
            filenames.  Can also be a single `str`/`pathlib.Path`,
            for a single image.
        dark_background (bool): default False which means follow theme,
            or pass true to force a darker coloured background.
    """

    def __init__(self, image_data, dark_background=False):
        super().__init__()
        if dark_background:
            self.setBackgroundBrush(QBrush(Qt.darkCyan))
        else:
            self.setStyleSheet("background: transparent")
            self.setBackgroundBrush(BackGrid())
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.scene = QGraphicsScene()
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImages(image_data)

    def updateImages(self, image_data):
        """Update the images new ones from filenames and optionally metadata.

        Args:
            image_data (None/list[dict]/list[str/pathlib.Path]/str/pathlib.Path):
                each dict has keys 'filename' and 'orientation' (and
                possibly others that are unused).  If 'filename' isn't
                present, we check for 'local_filename' instead.
                Currently every image is used and the list order
                determines the order.  That is subject to change.
                Can also be a list of `pathlib.Path` or `str` of image
                filenames.  Can also be a single `str`/`pathlib.Path`,
                for a single image.

        Raises:
            ValueError: an image did not load, for example if was empty.
            KeyError: dict did not have appropriate keys.
        """
        if isinstance(image_data, (str, Path)):
            image_data = [image_data]
        for img in self.imageGItem.childItems():
            self.imageGItem.removeFromGroup(img)
            self.scene.removeItem(img)
        img = None

        if image_data is not None:
            x = 0
            for data in image_data:
                if not isinstance(data, dict):
                    data = {"filename": data, "orientation": 0}
                filename = data.get("filename")
                if filename is None:
                    filename = data.get("local_filename")
                if filename is None:
                    raise KeyError(
                        f"Cannot find 'filename' nor 'local_filename' in {data}"
                    )
                qir = QImageReader(str(filename))
                # deal with jpeg exif rotations
                qir.setAutoTransform(True)
                pix = QPixmap(qir.read())
                if pix.isNull():
                    raise ValueError(f"Could not read an image from {filename}")
                rot = QTransform()
                rot.rotate(data["orientation"])
                pix = pix.transformed(rot)
                pixmap = QGraphicsPixmapItem(pix)
                pixmap.setTransformationMode(Qt.SmoothTransformation)
                pixmap.setPos(x, 0)
                pixmap.setVisible(True)
                sf = float(ScenePixelHeight) / float(pix.height())
                pixmap.setScale(sf)
                self.scene.addItem(pixmap)
                self.imageGItem.addToGroup(pixmap)
                # x += pixmap.boundingRect().width() + 10
                # TODO: some tools (manager?) had + 10 (maybe with darkbg?)
                x += sf * (pix.width() - 1.0)
                # TODO: don't floor here if units of scene are large!
                x = int(x)

        # Set sensible sizes and put into the view, and fit view to the image
        br = self.imageGItem.boundingRect()
        self.scene.setSceneRect(
            0,
            0,
            max(1000, br.width()),
            max(1000, br.height()),
        )
        self.setScene(self.scene)
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        """Left/right click to zoom in and out"""
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.zoomOut()
        else:
            self.zoomIn()
        self.centerOn(event.pos())

    def zoomOut(self):
        self.scale(0.8, 0.8)

    def zoomIn(self):
        self.scale(1.25, 1.25)

    def resetView(self):
        """Reset the view to its reasonable initial state."""
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)

    def rotateImage(self, dTheta):
        self.rotate(dTheta)
        # TODO: likely to decouple the zoom lock toggle
        self.resetView()
