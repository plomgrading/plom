from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import QDialog, QPushButton, QShortcut, QSizePolicy

from mlp_markentry import MarkEntry
from pageview import PageView
from mlp_useful import CommentWidget
from uiFiles.ui_annotator import Ui_annotator

class Annotator(QDialog):
    def __init__(self, fname, maxMark, parent=None):
        super(Annotator, self).__init__(parent)
        self.imageFile = fname
        self.maxMark = maxMark
        self.score = 0
        self.currentBackground = "border: 2px solid #008888; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop: 0 #00bbbb, stop: 1 #008888); "
        self.previousButton = None

        self.ui = Ui_annotator()
        self.ui.setupUi(self)
        self.setView()

        self.commentW = CommentWidget()
        self.ui.commentGrid.addWidget(self.commentW,1,1)

        self.setIcons()
        self.setButtons()
        self.setMarkEntry()

    def setView(self):
        self.view = PageView(self, self.imageFile)
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)
        self.showMaximized()
        self.view.fitInView(self.view.scene.sceneRect(), Qt.KeepAspectRatioByExpanding)
        self.view.centerOn(0, 0)

    def keyPressEvent(self, event):
        if not event.key() == Qt.Key_Escape:
            super(Annotator, self).keyPressEvent(event)

    def setMode(self, newMode, newCursor):
        if self.previousButton is None:
            pass
        else:
            self.previousButton.setStyleSheet("")

        if self.sender() == self.markEntry:
            self.previousButton=None
        else:
            self.previousButton = self.sender()
            self.previousButton.setStyleSheet(self.currentBackground)
        self.view.setMode(newMode)
        self.view.setCursor(newCursor)
        self.repaint()

    def setIcons(self):
        self.setIcon(self.ui.penButton, "&pen", "icons/pen.svg")
        self.setIcon(self.ui.lineButton, "&line", "icons/line.svg")
        self.setIcon(self.ui.boxButton, "&box", "icons/rectangle.svg")
        self.setIcon(self.ui.textButton, "&text", "icons/text.svg")
        self.setIcon(self.ui.tickButton, "&vtick", "icons/tick.svg")
        self.setIcon(self.ui.crossButton, "&xcross", "icons/cross.svg")
        self.setIcon(self.ui.deleteButton, "&delete", "icons/delete.svg")
        self.setIcon(self.ui.moveButton, "&move", "icons/move.svg")
        self.setIcon(self.ui.zoomButton, "&zoom", "icons/zoom.svg")
        self.setIcon(self.ui.panButton, "p&an", "icons/pan.svg")
        self.setIcon(self.ui.undoButton, "&undo", "icons/undo.svg")
        self.setIcon(self.ui.redoButton, "&redo", "icons/redo.svg")
        QShortcut(QKeySequence("Ctrl+Z"), self.view, self.view.undo, context=Qt.WidgetShortcut)
        QShortcut(QKeySequence("Ctrl+Shift+z"), self.view, self.view.redo, context=Qt.WidgetShortcut)

    def setIcon(self, tb, txt, iconFile):
        tb.setText(txt)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        tb.setIcon(QIcon(QPixmap(iconFile)))
        tb.setIconSize(QSize(24, 24))
        tb.setMinimumWidth(60)

    def setButtons(self):
        self.ui.penButton.clicked.connect(lambda: self.setMode("pen", QCursor(Qt.ArrowCursor)))
        self.ui.lineButton.clicked.connect(lambda: self.setMode("line", QCursor(Qt.CrossCursor)))
        self.ui.boxButton.clicked.connect(lambda: self.setMode("box", QCursor(Qt.ArrowCursor)))
        self.ui.textButton.clicked.connect(lambda: self.setMode("text", QCursor(Qt.IBeamCursor)))
        self.ui.crossButton.clicked.connect(lambda: self.setMode("cross", QCursor(Qt.ArrowCursor)))
        self.ui.tickButton.clicked.connect(lambda: self.setMode("tick", QCursor(Qt.ArrowCursor)))
        self.ui.moveButton.clicked.connect(lambda: self.setMode("move", QCursor(Qt.OpenHandCursor)))
        self.ui.deleteButton.clicked.connect(lambda: self.setMode("delete", QCursor(Qt.ForbiddenCursor)))
        self.ui.zoomButton.clicked.connect(lambda: self.setMode("zoom", QCursor(Qt.SizeFDiagCursor)))
        self.ui.panButton.clicked.connect(lambda: (self.setMode("pan", QCursor(Qt.OpenHandCursor)), self.view.setDragMode(1)))
        self.ui.undoButton.clicked.connect(self.view.undo)
        self.ui.redoButton.clicked.connect(self.view.redo)
        self.ui.finishedButton.clicked.connect(lambda:(self.commentW.saveComments(), self.closeEvent()))
        self.ui.cancelButton.clicked.connect(self.reject)

        self.commentW.CL.commentSignal.connect(self.handleComment)

    def handleComment(self, txt):
        self.setMode("text", QCursor(Qt.IBeamCursor))
        print("Type = {}".format(type(txt)))
        self.view.makeComment(txt)

    def setMarkEntry(self):
        self.markEntry = MarkEntry(self.maxMark)
        self.ui.markGrid.addWidget(self.markEntry,1,1)
        self.markEntry.markSetSignal.connect(self.totalMarkSet)
        self.markEntry.deltaSetSignal.connect(self.deltaMarkSet)
        self.view.scene.markChangedSignal.connect(self.changeMark)

    def totalMarkSet(self, tm):
        self.score = tm
        self.ui.finishedButton.setFocus()

    def deltaMarkSet(self, dm):
        lookingAhead = self.score+dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.panButton.animateClick()
            return
        self.setMode("delta", QCursor(Qt.ArrowCursor))
        self.view.markDelta(dm)

    def changeMark(self, dm):
        self.score += dm
        self.markEntry.setMark(self.score)
        self.markEntry.repaint()
        lookingAhead = self.score+dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.panButton.animateClick()

    def closeEvent(self):
        self.view.save()
        self.accept()
