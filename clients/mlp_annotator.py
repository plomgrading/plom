import sys
import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap, QCloseEvent
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QMessageBox, QPushButton, QShortcut, QSizePolicy, QTableWidget, QTableWidgetItem, QGridLayout

from mlp_markentry import MarkEntry
from pageview import PageView
from mlp_useful import CommentWidget, SimpleMessage
from uiFiles.ui_annotator_lhm import Ui_annotator_lhm
from uiFiles.ui_annotator_rhm import Ui_annotator_rhm

class Annotator(QDialog):
    def __init__(self, fname, maxMark, markStyle, mouseHand, parent=None):
        super(Annotator, self).__init__(parent)
        self.imageFile = fname
        self.maxMark = maxMark
        self.score = 0
        self.markStyle = markStyle
        self.currentBackground = "border: 2px solid #008888; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop: 0 #00bbbb, stop: 1 #008888); "
        self.previousButton = None

        # right-hand mouse = 0, left-hand mouse = 1
        if mouseHand == 0:
            self.ui = Ui_annotator_rhm()
        else:
            self.ui = Ui_annotator_lhm()

        self.ui.setupUi(self)
        self.setView()

        self.commentW = CommentWidget()
        self.ui.commentGrid.addWidget(self.commentW, 1, 1)

        self.setIcons()
        self.setButtons()
        # pass the marking style to the mark entry widget.
        self.setMarkEntry(self.markStyle)
        self.view.scene.scoreBox.changeMax(self.maxMark)
        self.view.scene.scoreBox.changeScore(self.score)
        # pass this to the comment table too
        self.commentW.setStyle(self.markStyle)
        self.commentW.changeMark(self.maxMark, self.score)

        self.showMaximized()

        ## Hot-key presses for various functions.
        self.keycodes = {
            # home-row
            Qt.Key_A: lambda: self.ui.zoomButton.animateClick(),
            Qt.Key_S: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_D: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_F: lambda: (self.commentW.currentItem(), self.commentW.CL.handleClick()),
            Qt.Key_G: lambda: self.ui.textButton.animateClick(),
            # lower-row
            Qt.Key_Z: lambda: self.ui.moveButton.animateClick(),
            Qt.Key_X: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_C: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_V: lambda: (self.commentW.nextItem(), self.commentW.CL.handleClick()),
            Qt.Key_B: lambda: self.ui.lineButton.animateClick(),
            # upper-row
            Qt.Key_Q: lambda: self.ui.panButton.animateClick(),
            Qt.Key_W: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_E: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_R: lambda: (self.commentW.previousItem(), self.commentW.CL.handleClick()),
            Qt.Key_T: lambda: self.ui.penButton.animateClick(),

            # and then the same but for the left-handed
            Qt.Key_H: lambda: self.ui.textButton.animateClick(),
            Qt.Key_J: lambda: (self.commentW.currentItem(), self.commentW.CL.handleClick()),
            Qt.Key_K: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_L: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_Semicolon: lambda: self.ui.zoomButton.animateClick(),

            Qt.Key_N: lambda: self.ui.lineButton.animateClick(),
            Qt.Key_M: lambda: (self.commentW.nextItem(), self.commentW.CL.handleClick()),
            Qt.Key_Comma: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_Period: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_Slash: lambda: self.ui.moveButton.animateClick(),

            Qt.Key_Y: lambda: self.ui.penButton.animateClick(),
            Qt.Key_U: lambda: (self.commentW.previousItem(), self.commentW.CL.handleClick()),
            Qt.Key_I: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_O: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_P: lambda: self.ui.panButton.animateClick(),

            # Then maximize and mark buttons
            Qt.Key_Plus: lambda: self.swapMaxNorm(),
            Qt.Key_Backslash: lambda: self.swapMaxNorm(),
            Qt.Key_Minus: lambda: self.view.zoomOut(),
            Qt.Key_Equal: lambda: self.view.zoomIn(),
            Qt.Key_QuoteLeft: lambda: self.keyToChangeMark(0),
            Qt.Key_0: lambda: self.keyToChangeMark(0),
            Qt.Key_1: lambda: self.keyToChangeMark(1),
            Qt.Key_2: lambda: self.keyToChangeMark(2),
            Qt.Key_3: lambda: self.keyToChangeMark(3),
            Qt.Key_4: lambda: self.keyToChangeMark(4),
            Qt.Key_5: lambda: self.keyToChangeMark(5),

            # Then list keys
            Qt.Key_Question: lambda: self.keyPopUp()
        }

    def keyPopUp(self):
        keylist = {'a': 'Zoom', 's': 'Undo', 'd': 'Tick/QMark/Cross', 'f': 'Current Comment', 'g': 'Text',
                   'z': 'Move', 'x': 'Delete', 'c': 'Box/Whitebox', 'v': 'Next Comment', 'b': 'Line/Arrow', 'q': 'Pan',  'w': 'Redo',  'e': 'Cross/QMark/Tick', 'r': 'Previous Comment', 't': 'Pen/Highlighter',
                   '+': 'Maximize Window', '\\': 'Maximize Window', '-': 'Zoom Out', '=': 'Zoom In',
                   '`': 'Set Mark 0', '0': 'Set Mark 0', '1': 'Set Mark 1', '2': 'Set Mark 2',
                   '3': 'Set Mark 3', '4': 'Set Mark 4', '5': 'Set Mark 5',
                    ';': 'Zoom', 'l': 'Undo', 'k': 'Tick/QMark/Cross', 'j': 'Current Comment', 'h': 'Text',
                    '/': 'Move', '.': 'Delete', ',': 'Box/Whitebox', 'm':'Next Comment', 'n':'Line/Arrow',
                    'p': 'Pan', 'o': 'Redo', 'i': 'Cross/QMark/Tick', 'u': 'Previous Comment', 'y': 'Pen/Highlighter',
                    '?': 'Key Help'}

        kp = QDialog()
        grid = QGridLayout()
        kt = QTableWidget()
        kt.setColumnCount(2)
        kt.setSortingEnabled(True)
        for a in keylist.keys():
            r = kt.rowCount()
            kt.setRowCount(r+1)
            kt.setItem(r,0,QTableWidgetItem(a))
            kt.setItem(r,1,QTableWidgetItem("{}".format(keylist[a])))

        kt.setHorizontalHeaderLabels(['key','function'])
        kt.verticalHeader().hide()
        kt.setEditTriggers(QAbstractItemView.NoEditTriggers)

        cb = QPushButton("&close")
        cb.clicked.connect(kp.accept)
        grid.addWidget(kt,1,1,3,3)
        grid.addWidget(cb,4,3)
        kp.setLayout(grid)
        kp.exec_()

    def setView(self):
        self.view = PageView(self, self.imageFile)
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
        self.view.fitInView(self.view.scene.sceneRect(), Qt.KeepAspectRatioByExpanding)
        self.view.centerOn(0, 0)

    def swapMaxNorm(self):
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def keyToChangeMark(self, buttonNumber):
        if self.markEntry.style == 'Up':
            self.markEntry.markButtons['p{}'.format(buttonNumber)].animateClick()
        elif self.markEntry.style == 'Down' and buttonNumber>0:
            self.markEntry.markButtons['m{}'.format(buttonNumber)].animateClick()

    def keyPressEvent(self, event):
        self.keycodes.get(event.key(), lambda *args: None)()

        if event.key() != Qt.Key_Escape:
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
        self.setIcon(self.ui.penButton, "pen", "{}/pen.svg".format(base_path))
        self.setIcon(self.ui.lineButton, "line", "{}/line.svg".format(base_path))
        self.setIcon(self.ui.boxButton, "box", "{}/rectangle.svg".format(base_path))
        self.setIcon(self.ui.textButton, "text", "{}/text.svg".format(base_path))
        self.setIcon(self.ui.tickButton, "tick", "{}/tick.svg".format(base_path))
        self.setIcon(self.ui.crossButton, "cross", "{}/cross.svg".format(base_path))
        self.setIcon(self.ui.deleteButton, "delete", "{}/delete.svg".format(base_path))
        self.setIcon(self.ui.moveButton, "move", "{}/move.svg".format(base_path))
        self.setIcon(self.ui.zoomButton, "zoom", "{}/zoom.svg".format(base_path))
        self.setIcon(self.ui.panButton, "pan", "{}/pan.svg".format(base_path))
        self.setIcon(self.ui.undoButton, "undo", "{}/undo.svg".format(base_path))
        self.setIcon(self.ui.redoButton, "redo", "{}/redo.svg".format(base_path))
        self.setIcon(self.ui.commentButton, "com", "{}/comment.svg".format(base_path))
        self.setIcon(self.ui.commentUpButton, "com up", "{}/comment_up.svg".format(base_path))
        self.setIcon(self.ui.commentDownButton, "com dn", "{}/comment_down.svg".format(base_path))

        self.endShortCut = QShortcut(QKeySequence("Alt+Enter"), self)
        self.endShortCut.activated.connect(self.endAndRelaunch)
        self.endShortCutb = QShortcut(QKeySequence("Alt+Return"), self)
        self.endShortCutb.activated.connect(self.endAndRelaunch)


    @pyqtSlot()
    def endAndRelaunch(self):
        self.commentW.saveComments()
        self.closeEvent(True)

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

        self.ui.keyHelpButton.clicked.connect(self.keyPopUp)


        self.ui.commentButton.clicked.connect(lambda: (self.commentW.currentItem(), self.commentW.CL.handleClick()))
        self.ui.commentUpButton.clicked.connect(lambda: (self.commentW.previousItem(), self.commentW.CL.handleClick()))
        self.ui.commentDownButton.clicked.connect(lambda: (self.commentW.nextItem(), self.commentW.CL.handleClick()))

        self.ui.finishedButton.clicked.connect(lambda:(self.commentW.saveComments(), self.closeEvent(True)))
        self.ui.finishNoRelaunchButton.clicked.connect(lambda:(self.commentW.saveComments(), self.closeEvent(False)))

        self.ui.cancelButton.clicked.connect(self.reject)

        self.commentW.CL.commentSignal.connect(self.handleComment)


    def handleComment(self, dlt_txt):
        self.setMode("text", QCursor(Qt.IBeamCursor))
        # set the delta to 0 if it is out-of-bounds.
        delta=int(dlt_txt[0])
        if self.markStyle == 2:  # mark up - disable negative
            if delta <= 0 or delta + self.score > self.maxMark:
                self.view.makeComment(0, dlt_txt[1])
                return
        elif self.markStyle == 2:  # mark down - disable positive
            if delta >= 0 or delta + self.score < 0:
                self.view.makeComment(0, dlt_txt[1])
                return
        # Remaining possibility = mark total, enable all.
        self.view.makeComment(dlt_txt[0], dlt_txt[1])

    def setMarkEntry(self, markStyle):
        self.markEntry = MarkEntry(self.maxMark)
        self.ui.markGrid.addWidget(self.markEntry, 1, 1)
        self.markEntry.markSetSignal.connect(self.totalMarkSet)
        self.markEntry.deltaSetSignal.connect(self.deltaMarkSet)
        self.view.scene.markChangedSignal.connect(self.changeMark)
        self.markEntry.setStyle(markStyle)

    def totalMarkSet(self, tm):
        self.score = tm
        self.ui.finishedButton.setFocus()
        self.view.scene.scoreBox.changeScore(self.score)
        self.commentW.changeMark(self.maxMark, self.score)

    def deltaMarkSet(self, dm):
        lookingAhead = self.score+dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.moveButton.animateClick()
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
            self.ui.moveButton.animateClick()

    def closeEvent(self,relaunch):
        if type(relaunch) == QCloseEvent:
            self.launchAgain=False
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
            if relaunch:
                self.launchAgain = True
            else:
                self.launchAgain = False

            self.view.save()
            self.accept()
