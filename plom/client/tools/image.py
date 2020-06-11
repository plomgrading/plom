import base64

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QImage, QPen, QColor, QBrush, QPixmap
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem, QGraphicsTextItem, \
    QGraphicsPixmapItem, QGraphicsObject

from plom.client.tools import CommandMoveItem


class CommandImage(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, pt, image):
        super(CommandImage, self).__init__()
        self.scene = scene
        self.pt = pt
        self.image = image
        self.ImageItem = ImageItemObject(self.pt, image)
        self.setText("Image")

    def redo(self):
        self.imageItem.flash_redo()
        self.scene.addItem(self.imageItem.ci)

    def undo(self):
        self.imageItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.imageItem.ci))


class ImageItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt, image):
        super(ImageItemObject, self, image).__init__()
        self.ci = ImageItem(pt, self, image)

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()


class ImageItem(QGraphicsPixmapItem):
    def __init__(self, pt, image, parent=None):
        super(ImageItem, self).__init__()
        pixmap = QGraphicsPixmapItem(QPixmap.fromImage(image))
        pixmap.setPos(pt)
        self.pt = pt
        pixmap.setFlag(QGraphicsItem.ItemIsMovable)
        pixmap.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
    #
    # def itemChange(self, change, value):
    #     if change == QGraphicsItem.ItemPositionChange and self.scene():
    #         command = CommandMoveItem(self, value)
    #         self.scene().undoStack.push(command)
    #     return QGraphicsPixmapItem.itemChange(self, change, value)

    def pickle(self):
        return ["Image", base64.b64encode(self.image)]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
            # paint the normal item with the default 'paint' method
        super(ImageItem, self).paint(painter, option, widget)
