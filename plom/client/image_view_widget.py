# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtGui import QBrush, QColor, QImageReader, QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import (
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


def mousewheel_delta_to_scale(d):
    """Certain mousewheel events produce "delta", change that into an appropriate scale value.

    Args:
        d (int): a signed delta value, e.g., from a `QGraphicsSceneWheelEvent`.

    Returns:
        float: e.g., 1.1 to zoom in and 0.90909 to zoom out.

    Observations on the delta value:

    - Wayland: cheap bluetooth mouse is 120 (sometimes 240)
    - Wayland: generic lenovo USB mouse is same
    - Wayland: Thinkpad trackpoint: pressure sensitive, 12 up to maybe 200
    - Windows 10: I also observed 120/-120 with same bluetooth mouse

    We threshold the in [-300, 300].  The 800 constant is tweakable.
    In theory one could allow user to tweak scaling speed / direction.
    """
    if d < 0:
        d = max(-300, d)
        s = 800.0 / (800.0 + abs(d))
    else:
        d = min(300, d)
        s = (800.0 + abs(d)) / 800.0
    return s


class ImageViewWidget(QWidget):
    """Simple view widget for pageimages to be embedded in other windows.

    Args:
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
        has_controls (bool): include UI elements for zooming etc.
            Default: True.
        has_rotate_controls (bool): include UI elements for rotation.
            Default: True.  Does nothing unless `has_controls` is True.
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
        has_controls=True,
        has_rotate_controls=True,
        compact=True,
        dark_background=False,
    ):
        super().__init__(parent)
        # Grab an examview widget (a interactive subclass of QGraphicsView)
        self.view = _ExamView(image_data, dark_background=dark_background)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        grid = QVBoxLayout()
        if compact:
            grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.view, 1)
        grid.setSpacing(3)
        self.zoomLockB = None
        if has_controls:
            resetB = QToolButton()
            # resetB.setText("\N{Leftwards Arrow To Bar Over Rightwards Arrow To Bar}")
            # resetB.setText("\N{Up Down Black Arrow}")
            resetB.setText("reset")
            resetB.setToolTip("reset zoom")
            resetB.clicked.connect(self.resetView)
            zoomInB = QToolButton()
            zoomInB.setText("\N{HEAVY PLUS SIGN}")
            zoomInB.setToolTip("zoom in")
            zoomInB.clicked.connect(self.zoomIn)
            zoomOutB = QToolButton()
            zoomOutB.setText("\N{HEAVY MINUS SIGN}")
            zoomOutB.setToolTip("zoom out")
            zoomOutB.clicked.connect(self.zoomOut)
            zoomLockB = QToolButton()
            zoomLockB.setText(" \N{LOCK} ")
            zoomLockB.setCheckable(True)
            zoomLockB.setChecked(False)
            zoomLockB.clicked.connect(self.zoomLockToggle)
            self.zoomLockB = zoomLockB
            self._zoomLockUpdateTooltip()
            buttons = QHBoxLayout()
            buttons.setContentsMargins(0, 0, 0, 0)
            buttons.setSpacing(3)
            buttons.addStretch(1)
            buttons.addWidget(resetB)
            buttons.addWidget(zoomInB)
            buttons.addWidget(zoomOutB)
            buttons.addWidget(zoomLockB)
            if has_rotate_controls:
                rotateB_cw = QToolButton()
                rotateB_cw.setText("\N{CLOCKWISE OPEN CIRCLE ARROW}")
                rotateB_cw.setToolTip("rotate clockwise")
                rotateB_cw.clicked.connect(lambda: self.view.rotateImage(-90))
                rotateB_ccw = QToolButton()
                rotateB_ccw.setText("\N{ANTICLOCKWISE OPEN CIRCLE ARROW}")
                rotateB_ccw.setToolTip("rotate counter-clockwise")
                rotateB_ccw.clicked.connect(lambda: self.view.rotateImage(90))
                buttons.addSpacing(12)
                buttons.addWidget(rotateB_cw)
                buttons.addWidget(rotateB_ccw)
            buttons.addStretch(1)
            grid.addLayout(buttons)

        self.setLayout(grid)

    def updateImage(self, image_data, keep_zoom=False):
        """Pass file(s) to the view to update the image.

        Args:
            image_data: documented elsewhere

        Keyword Args:
            keep_zoom (bool): by default (when `False`) we reset the
                view to the default on new images.  Pass `True` if you
                want to instead try to maintain the current zoom and
                pan; but be aware if the new images have changed in
                number or in resolution, then the result may be
                poor or ill-defined.  If there was no previous image
                the underlying view will ignore our request.

        Returns:
            None
        """
        self.view.updateImages(image_data, keep_zoom)
        if not keep_zoom:
            # to reset the view lock icon
            self.resetView()

    def get_orientation(self):
        """Report the sum of user-performed rotations as counter-clockwise angle in degrees."""
        return self.view.theta

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
        self.zoomLockSetOn()

    def zoomOut(self):
        self.view.zoomOut()
        self.zoomLockSetOn()

    def zoomLockToggle(self):
        if self.zoomLockB and not self.zoomLockB.isChecked():
            # refit the view on untoggle
            self.resetView()
        self._zoomLockUpdateTooltip()

    def zoomLockSetOn(self):
        if self.zoomLockB:
            self.zoomLockB.setChecked(True)
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


class _ExamScene(QGraphicsScene):
    """Subclass the qgraphicsscene to override the wheel-event and so trigger nice scroll-to-zoom behaviour."""

    def wheelEvent(self, event):
        if (
            QGuiApplication.queryKeyboardModifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            s = mousewheel_delta_to_scale(event.delta())
            self.views()[0].scale(s, s)
            # Unpleasant to grub in parent but want mouse events to lock zoom
            self.views()[0].parent().zoomLockSetOn()
            event.accept()


class _ExamView(QGraphicsView):
    """Display images with some interaction: click-to-zoom/unzoom.

    Args:
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
            self.setBackgroundBrush(QBrush(QColor("darkCyan")))
        else:
            self.setStyleSheet("background: transparent")
            self.setBackgroundBrush(BackGrid())
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scene = _ExamScene()
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        # we track the total user-performed rotations in case caller is interested
        self.theta = 0
        self.updateImages(image_data)

    def updateImages(self, image_data, keep_zoom=False):
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

        Keyword Args:
                keep_zoom (bool): if we already have an image, try to
                leave it alone and replace with a new one without
                changing the zoom or pan.  Default: False.

        Raises:
            ValueError: an image did not load, for example if was empty, or
                the filename was empty.
            KeyError: dict did not have appropriate keys.
        """
        if isinstance(image_data, (str, Path)):
            image_data = [image_data]
        if len(self.imageGItem.childItems()) < 1:
            # no previous image: do not honour request to persist zoom
            keep_zoom = False
        for img in self.imageGItem.childItems():
            self.imageGItem.removeFromGroup(img)
            self.scene.removeItem(img)
        img = None

        # we may use the viewing angle instead of rotating the item so reset
        # if we have new images, even if they have non-zero orientation
        if not keep_zoom:
            self.resetTransform()

        if image_data is not None:
            x = 0
            for data in image_data:
                if not isinstance(data, dict):
                    data = {"filename": data, "orientation": 0}
                if not ("filename" in data.keys() or "local_filename" in data.keys()):
                    raise KeyError(
                        f"Cannot find 'filename' nor 'local_filename' in {data}"
                    )
                filename = data.get("filename")

                if not filename:
                    filename = data.get("local_filename")
                if not filename:
                    raise ValueError(f"data row {data} has no nonempty filename")
                qir = QImageReader(str(filename))
                # deal with jpeg exif rotations
                qir.setAutoTransform(True)
                pix = QPixmap(qir.read())
                if pix.isNull():
                    raise ValueError(f"Could not read an image from '{filename}'")
                rot = QTransform()
                # if more than one image, its not well-defined which one theta gets
                self.theta = data["orientation"]
                # 90 means CCW, but we have a minus sign b/c of a y-downward coordsys
                rot.rotate(-data["orientation"])
                pix = pix.transformed(rot)
                pixmap = QGraphicsPixmapItem(pix)
                pixmap.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
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

        if keep_zoom:
            return
        # Set sensible sizes and put into the view, and fit view to the image
        br = self.imageGItem.boundingRect()
        self.scene.setSceneRect(
            0,
            0,
            max(1000, br.width()),
            max(1000, br.height()),
        )
        self.setScene(self.scene)
        self.fitInView(self.imageGItem, Qt.AspectRatioMode.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        """Left/right click to zoom in and out."""
        if (event.button() == Qt.MouseButton.RightButton) or (
            QGuiApplication.queryKeyboardModifiers()
            == Qt.KeyboardModifier.ShiftModifier
        ):
            self.zoomOut()
        else:
            self.zoomIn()
        self.centerOn(event.position())
        # Unpleasant to grub in parent but want mouse events to lock zoom
        # TODO: instead use a signal/slot mechanism
        self.parent().zoomLockSetOn()
        return super().mouseReleaseEvent(event)

    def zoomOut(self):
        self.scale(0.8, 0.8)

    def zoomIn(self):
        self.scale(1.25, 1.25)

    def resetView(self):
        """Reset the view to its reasonable initial state."""
        self.fitInView(self.imageGItem, Qt.AspectRatioMode.KeepAspectRatio)

    def rotateImage(self, dTheta):
        # 90 means CCW, but we have a minus sign b/c of a y-downward coordsys
        self.rotate(-dTheta)
        self.theta += dTheta
        if self.theta == 360:
            self.theta = 0
        if self.theta == -90:
            self.theta = 270
        # Unpleasant to grub in parent but want to unlock zoom not just refit
        # TODO: instead use a signal/slot mechanism
        self.parent().resetView()
