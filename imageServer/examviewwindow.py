from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QGridLayout, QPushButton, QWidget


class ExamViewWindow(QWidget):
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.view = ExamView(fname)
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)

        self.resetB = QPushButton('reset view')
        self.resetB.clicked.connect(lambda: self.view.resetView())

        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 4)
        grid.addWidget(self.resetB, 20, 1)

        self.setLayout(grid)
        self.show()

    def updateImage(self, fname):
        self.view.updateImage(fname)


class ExamView(QGraphicsView):
    def __init__(self, fname):
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        self.scene = QGraphicsScene()
        self.image = QPixmap(fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(0, 0, max(1000, self.image.width()), max(1000, self.image.height()))
        self.scene.addItem(self.imageItem)
        self.setScene(self.scene)
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def updateImage(self, fname):
        self.image = QPixmap(fname)
        self.imageItem.setPixmap(self.image)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        if(event.button() == Qt.RightButton):
            self.scale(0.8, 0.8)
        else:
            self.scale(1.25, 1.25)

    def resetView(self):
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)
