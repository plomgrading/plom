import base64

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty, \
    QByteArray, QBuffer, QDataStream, QIODevice, QVariant
from PyQt5.QtGui import QFont, QImage, QPen, QColor, QBrush, QPixmap, \
    QImageReader
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem, QGraphicsTextItem, \
    QGraphicsPixmapItem, QGraphicsObject, QMessageBox, QInputDialog, \
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent

from plom.client.tools import CommandMoveItem


class CommandImage(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, pt, image, scale=1):
        super(CommandImage, self).__init__()
        self.scene = scene
        self.pt = pt
        self.image = image
        self.imageItem = ImageItemObject(self.pt, self.image, scale)
        self.setText("Image")

    def redo(self):
        self.imageItem.flash_redo()
        self.scene.addItem(self.imageItem.ci)

    def undo(self):
        self.imageItem.flash_undo()
        QTimer.singleShot(200,
                          lambda: self.scene.removeItem(
                              self.imageItem.ci.pixmap))


class ImageItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt, image, scale):
        """

        Args:
            pt:
            image (QImage):
        """
        super(ImageItemObject, self).__init__()
        self.image = image
        self.ci = ImageItem(QPixmap.fromImage(image), pt, self, scale)
        self.anim = QPropertyAnimation(self, b"scale")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(1)
        self.anim.setKeyValueAt(2, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(2, 8)
        self.anim.setEndValue(3)
        self.anim.start()


class ImageItem(QGraphicsPixmapItem):
    def __init__(self, qpixmap, pt, parent, scale):
        super(ImageItem, self).__init__()
        self.setPixmap(qpixmap)
        self.setPos(pt)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.parent = parent
        self.setScale(scale)

    def pickle(self):
        ba = QByteArray()
        img = self.parent.image
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        img.save(buffer, 'PNG')
        pos = self.pos()
        pickle = ["Image", self.x(), self.y(),
                  str(ba.toBase64().data()), self.scale()]
        return pickle

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent'):
        scale, ok = QInputDialog().getInt(None, "Image Scaling",
                                          "Percentage:",
                                          value=int(self.scale() * 100), )
        if ok:
            self.setScale(scale / 100)
