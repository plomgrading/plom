import sys
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap, QCloseEvent
from PyQt5.QtWidgets import QDialog, QMessageBox, QPushButton, QShortcut, QSizePolicy

from mlp_markentry import MarkEntry
from pageview import PageView
from mlp_useful import CommentWidget, SimpleMessage
from uiFiles.ui_annotator import Ui_annotator

class Annotator(QDialog):
    def __init__(self, fname, maxMark, markStyle, parent=None):
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
        # pass the marking style to the mark entry widget.
        self.setMarkEntry(markStyle)
        self.view.scene.scoreBox.changeMax(self.maxMark)
        self.view.scene.scoreBox.changeScore(self.score)

    def setView(self):
        self.view = PageView(self, self.imageFile)
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
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
        ## pyinstaller creates a temp folder and stores path in _MEIPASS
        try:
            base_path = sys._MEIPASS
            # print("")
        except Exception:
            base_path = "./icons"

        #tweak path for loading the icons for use with pyinstaller one-file.
        self.setIcon(self.ui.penButton, "&pen", "{}/pen.svg".format(base_path))
        self.setIcon(self.ui.lineButton, "&line", "{}/line.svg".format(base_path))
        self.setIcon(self.ui.boxButton, "&box", "{}/rectangle.svg".format(base_path))
        self.setIcon(self.ui.textButton, "&text", "{}/text.svg".format(base_path))
        self.setIcon(self.ui.tickButton, "&vtick", "{}/tick.svg".format(base_path))
        self.setIcon(self.ui.crossButton, "&xcross", "{}/cross.svg".format(base_path))
        self.setIcon(self.ui.deleteButton, "&delete", "{}/delete.svg".format(base_path))
        self.setIcon(self.ui.moveButton, "&move", "{}/move.svg".format(base_path))
        self.setIcon(self.ui.zoomButton, "&zoom", "{}/zoom.svg".format(base_path))
        self.setIcon(self.ui.panButton, "p&an", "{}/pan.svg".format(base_path))
        self.setIcon(self.ui.undoButton, "&undo", "{}/undo.svg".format(base_path))
        self.setIcon(self.ui.redoButton, "&redo", "{}/redo.svg".format(base_path))
        QShortcut(QKeySequence("Ctrl+Z"), self.view, self.view.undo, context=Qt.WidgetShortcut)
        QShortcut(QKeySequence("Ctrl+Y"), self.view, self.view.redo, context=Qt.WidgetShortcut)
        QShortcut(QKeySequence("Alt+Return"), self.view,(lambda:(self.commentW.saveComments(), self.closeEvent())), context=Qt.WidgetShortcut)

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
        self.view.makeComment(txt)

    def setMarkEntry(self, markStyle):
        self.markEntry = MarkEntry(self.maxMark)
        self.ui.markGrid.addWidget(self.markEntry,1,1)
        self.markEntry.markSetSignal.connect(self.totalMarkSet)
        self.markEntry.deltaSetSignal.connect(self.deltaMarkSet)
        self.view.scene.markChangedSignal.connect(self.changeMark)
        self.markEntry.setStyle(markStyle)

    def totalMarkSet(self, tm):
        self.score = tm
        self.ui.finishedButton.setFocus()
        self.view.scene.scoreBox.changeScore(self.score)

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
        self.view.scene.scoreBox.changeScore(self.score)
        lookingAhead = self.score+dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.panButton.animateClick()

    def closeEvent(self,tmp = "blah"):
        if type(tmp) == QCloseEvent:
            self.reject()
        else:
            # if marking total or up, be careful of giving 0-marks
            if self.score == 0 and self.markEntry.style != 'Down':
                msg = SimpleMessage('You have given 0 - please confirm')
                if msg.exec_() == QMessageBox.No:
                    return
            # if marking down, be careful of giving max-marks
            if self.score == self.maxMark  and self.markEntry.style == 'Down':
                msg = SimpleMessage('You have given {} - please confirm'.format(self.maxMark))
                if msg.exec_() == QMessageBox.No:
                    return

            self.view.save()
            self.accept()
