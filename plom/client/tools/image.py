# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

from PyQt5.QtCore import QIODevice, QPointF, QBuffer, QByteArray
from PyQt5.QtGui import QBrush, QColor, QImage, QPixmap, QPen
from PyQt5.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
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

from plom.client.tools import CommandTool, DeleteObject, UndoStackMoveMixin


class CommandImage(CommandTool):
    """A class for making image commands."""

    def __init__(self, scene, pt, image, scale=1, border=True, data=None):
        """
        Initialize a new Image command.

        Args:
            scene (PageScene): the scene the image is being inserted into.
            pt (QPointF): the point of the top left corner of the image.
            image (QImage): the image being added to the scene.
            scale (float): the scaling value, <1 decreases size, >1 increases.
            border (bool): True if the image has a border, false otherwise.
            data (str): Base64 data held in a string if the image had
                previously been json serialized.
                TODO: what does it mean to be `None`, consider refactoring.
        """
        super().__init__(scene)
        self.obj = ImageItem(pt, image, scale, border, data)
        self.do = DeleteObject(self.obj.shape())
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
            raise ValueError("Encountered a problem loading image.")
        return cls(scene, QPointF(X[0], X[1]), img, X[3], X[4], X[2])


class ImageItem(UndoStackMoveMixin, QGraphicsPixmapItem):
    """
    An image added to a paper.
    """

    def __init__(self, pt, qImage, scale, border, data):
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
        super().__init__()
        self.qImage = qImage
        self.border = border
        self.setPixmap(QPixmap.fromImage(self.qImage))
        self.setPos(pt)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.saveable = True
        self.setScale(scale)
        self.data = data
        self.thick = 4

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
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            self.qImage.save(buffer, "PNG")
            pickle = [
                "Image",
                self.x(),
                self.y(),
                str(byte_array.toBase64().data()),
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
        # yuck, had to go way up the chain to find someone who can parent a dialog!
        # maybe that means this code should NOT be opening dialogs
        parent = self.scene().views()[0]
        dialog = ImageSettingsDialog(parent, int(self.scale() * 100), self.border)
        if dialog.exec():
            scale, border = dialog.getSettings()
            self.setScale(scale / 100)
            # TODO: I don't think this event generates a Command!  No undo stack...
            # self.scene()._set_dirty()
            if border is not self.border:
                self.border = border
                if self.border:  # update border thickness
                    self.thick = 4
                else:
                    self.thick = 0
            self.update()  # trigger update


class ImageSettingsDialog(QDialog):
    """Menu dialog for Image Settings."""

    NumGridRows = 2
    NumButtons = 3

    def __init__(self, parent, scalePercent, checked):
        """
        Initialize a new image settings dialog object.

        Args:
            scalePercent (int): Scale of the image (as a percentage)
            checked (bool): True if the image currently has a red border,
                False otherwise.
        """
        super().__init__(parent)
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
