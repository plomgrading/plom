# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Andrew Rechnitzer

from PyQt5.QtCore import (
    QTimer,
    QPropertyAnimation,
    QByteArray,
    QBuffer,
    QIODevice,
    QPoint,
    QPointF,
    pyqtProperty,
)
from PyQt5.QtGui import QBrush, QColor, QImage, QPixmap, QPen
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
    QDialog,
    QSpinBox,
    QCheckBox,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)


class CommandImage(QUndoCommand):
    """ A class for making image commands. """

    def __init__(self, scene, pt, image, scale=1, border=True, data=None):
        """
        Initialize a new Image command.

        Args:
            scene (PageScene): the scene the image is being inserted into.
            pt (QPoint): the point of the top left corner of the image.
            image (QImage): the image being added to the scene.
            scale (float): the scaling value, <1 decreases size, >1 increases.
            border (bool): True if the image has a border, false otherwise.
            data (str): Base64 data held in a string if the image had
                previously been json serialized.
        """
        super(CommandImage, self).__init__()
        self.scene = scene
        self.width = image.width()
        if data is None:
            toMidpoint = QPoint(-image.width() / 2, -image.height() / 2)
            self.midPt = pt + toMidpoint
        else:
            self.midPt = pt
        self.image = image
        self.imageItem = ImageItemObject(self.midPt, self.image, scale, border, data)
        self.setText("Image")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandImage from a serialized form."""
        assert X[0] == "Image"
        X = X[1:]
        if len(X) != 5:
            raise ValueError("wrong length of pickle data")
        # extract data from encoding
        # TODO: sus arithmetic here
        data = QByteArray().fromBase64(bytes(X[2][2 : len(X[2]) - 2], encoding="utf-8"))
        img = QImage()
        if not img.loadFromData(data):
            log.error("Encountered a problem loading image.")
            raise ValueError("Encountered a problem loading image.")
        return cls(scene, QPointF(X[0], X[1]), img, X[3], X[4], X[2])

    def redo(self):
        """ Redoes adding the image to the scene. """
        self.imageItem.flash_redo()
        self.scene.addItem(self.imageItem.ci)

    def undo(self):
        """ Undoes adding the image to the scene. """
        self.imageItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.imageItem.ci))


class ImageItemObject(QGraphicsObject):
    """A class which encapsulates the QImage.

    Used primarily for animation when undo or redo is performed.
    """

    def __init__(self, midPt, image, scale, border, data):
        """
        Initializes an new ImageItemObject.

        Args:
            midPt (QPoint): the point middle of the image.
            image (QImage): the image being added to the scene.
            scale (float): the scaling value, <1 decreases size, >1 increases.
            border (bool): True if the image has a border, false otherwise.
            data (str): Base64 data held in a string if the image had
                previously been json serialized.
        """
        super(ImageItemObject, self).__init__()
        self.ci = ImageItem(midPt, image, self, scale, border, data)
        self.anim = QPropertyAnimation(self, b"thickness")
        self.border = border

    def flash_undo(self):
        """Animates the object in an undo sequence."""
        self.anim.setDuration(200)
        if self.ci.border:
            self.anim.setStartValue(4)
        else:
            self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        """Animates the object in a redo sequence. """
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        if self.ci.border:
            self.anim.setEndValue(4)
        else:
            self.anim.setEndValue(0)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.ci.thick

    @thickness.setter
    def thickness(self, value):
        self.ci.thick = value
        self.ci.update()


class ImageItem(QGraphicsPixmapItem):
    """
    An image added to a paper.
    """

    def __init__(self, midPt, qImage, parent, scale, border, data):
        """
        Initialize a new ImageItem.

        Args:
            pt (QPoint): the point of the top left corner of the image.
            qImage (QImage): the image being added to the scene.
            scale (float): the scaling value, <1 decreases size, >1 increases.
            border (bool): True if the image has a border, false otherwise.
            data (str): Base64 data held in a string if the image had
                previously been json serialized.
        """
        super(ImageItem, self).__init__()
        self.qImage = qImage
        self.border = border
        self.setPixmap(QPixmap.fromImage(self.qImage))
        self.setPos(midPt)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.parent = parent
        self.setScale(scale)
        self.data = data
        self.thick = 0

    def paint(self, painter, option, widget=None):
        """
        Paints the scene by adding a red border around the image if applicable.
        """
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)

        super().paint(painter, option, widget)
        if self.thick > 0:
            painter.save()
            painter.setPen(QPen(QColor("red"), self.thick))
            painter.drawRect(self.boundingRect())
            painter.restore()

    def pickle(self):
        """
        Pickle the image into a list containing important information.

        Returns:
            (list): containing
                (str): "Image"
                (float): X position of image.
                (float): Y position of image.
                (str): a string containing image data in base64 encoding.
                (float): scale of the image.
                (bool): true if the image contains a red border,
                    false otherwise.
        """
        if self.data is None:
            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.WriteOnly)
            self.qImage.save(buffer, "PNG")
            pickle = [
                "Image",
                self.x(),
                self.y(),
                str(ba.toBase64().data()),
                self.scale(),
                self.border,
            ]
        else:
            pickle = ["Image", self.x(), self.y(), self.data, self.scale(), self.border]
        return pickle

    def mouseDoubleClickEvent(self, event: "QGraphicsSceneMouseEvent"):
        """
        On double-click, show menu and modify image according to user inputs.

        Args:
            event (QMouseEvent): the double mouse click.

        Returns:
            None
        """
        dialog = ImageSettingsDialog(int(self.scale() * 100), self.border)
        if dialog.exec():
            scale, border = dialog.getSettings()
            self.setScale(scale / 100)
            if border is not self.border:
                self.border = border
                if self.border:  # update border thickness
                    self.thick = 4
                else:
                    self.thick = 0
                self.update()  # trigger update


class ImageSettingsDialog(QDialog):
    """ Menu dialog for Image Settings. """

    NumGridRows = 2
    NumButtons = 3

    def __init__(self, scalePercent, checked):
        """
        Initialize a new image settings dialog object.

        Args:
            scalePercent (int): Scale of the image (as a percentage)
            checked (bool): True if the image currently has a red border,
                False otherwise.
        """
        super(ImageSettingsDialog, self).__init__()
        self.createFormGroupBox(scalePercent, checked)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.formGroupBox)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        self.setWindowTitle("Image Settings")

    def createFormGroupBox(self, scalePercent, checked):
        """
        Build the form Box.

        Args:
            scalePercent (int): Scale of the image (as a percentage)
            checked (bool): True if the image currently has a red border,
                False otherwise.
        Returns:
            None

        """
        self.formGroupBox = QGroupBox("Image Settings")
        layout = QFormLayout()
        self.scaleButton = QSpinBox()
        self.scaleButton.setRange(1, 500)
        self.scaleButton.setValue(scalePercent)
        layout.addRow(QLabel("Scale"), self.scaleButton)
        self.checkBox = QCheckBox()
        self.checkBox.setChecked(checked)
        layout.addRow(QLabel("Include Red Border"), self.checkBox)
        self.formGroupBox.setLayout(layout)

    def getSettings(self):
        """
        Return the settings held in the dialog box.

        Notes:
            Even if the user presses Cancel, the values will still be held
            by the dialog box. Make sure to ensure exec() returns true
            before accessing these values.
        Returns:
            (int): the scale of the image that the user has chosen.
            (bool): True if user wants image to have a red border,
                False otherwise.
        """
        return self.scaleButton.value(), self.checkBox.isChecked()
