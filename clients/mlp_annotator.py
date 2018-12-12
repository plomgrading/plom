import sys

from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap, QCloseEvent
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QMessageBox, \
    QPushButton, QShortcut, QTableWidget, QTableWidgetItem, QGridLayout

from mark_handler import MarkHandler
from pageview import PageView
from useful_classes import CommentWidget, SimpleMessage
from uiFiles.ui_annotator_lhm import Ui_annotator_lhm
from uiFiles.ui_annotator_rhm import Ui_annotator_rhm

# Short descriptions of each tool to display to user.
modeLines = {
    'box': 'L: highlighted box. R: opaque white box.',
    'comment': 'L: paste comment and associated mark.',
    'cross': 'L: cross. M: ?-mark. R: checkmark.',
    'delta': 'L: paste mark. M: ?-mark. R: checkmark/cross.',
    'delete': 'Delete object.',
    'line': 'L: straight line. R: arrow.',
    'move': 'Move object.',
    'pan': 'Pan view.',
    'pen': 'L: freehand pen. R: freehand highlighter.',
    'text': 'Text. Enter: newline, Shift-Enter/ESC: finish.',
    'tick': 'L: checkmark. M: ?-mark. R: cross.',
    'zoom': 'L: Zoom in. R: zoom out.',
    }


class Annotator(QDialog):
    """The main annotation window for annotating group-images
    and assigning marks.
    """
    def __init__(self, fname, maxMark, markStyle, mouseHand, parent=None):
        super(Annotator, self).__init__(parent)
        # Grab filename of image, max mark, mark style (total/up/down)
        # and mouse-hand (left/right)
        self.imageFile = fname
        self.maxMark = maxMark
        self.markStyle = markStyle
        # Set current mark to 0.
        self.score = 0
        # make styling of currently selected button/tool.
        self.currentButtonStyleBackground = "border: 2px solid #00aaaa; " \
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, " \
            "stop: 0 #00dddd, stop: 1 #00aaaa);"
        # when comments are used, we just outline the comment list - not
        # the whole background - so make a style for that.
        self.currentButtonStyleOutline = "border: 2px solid #00aaaa; "
        # No button yet selected.
        self.currentButton = None
        # Window depends on mouse-hand - si
        # right-hand mouse = 0, left-hand mouse = 1
        if mouseHand == 0:
            self.ui = Ui_annotator_rhm()
        else:
            self.ui = Ui_annotator_lhm()
        # Set up the gui.
        self.ui.setupUi(self)
        # Set up the view of the group-image - loads in the image etc
        self.setView()
        # Create the comment list widget and put into gui.
        self.commentW = CommentWidget()
        self.ui.commentGrid.addWidget(self.commentW, 1, 1)
        # Set the tool icons
        self.setIcons()
        # Connect all the buttons to relevant functions
        self.setButtons()
        # pass the marking style to the mark entry widget.
        self.setmarkHandler(self.markStyle)
        # Set up the score-box that gets stamped in top-left of image.
        # "k out of n" where k=current score, n = max score.
        self.view.scene.scoreBox.changeMax(self.maxMark)
        self.view.scene.scoreBox.changeScore(self.score)
        # pass this to the comment table too - it needs to know if we are
        # marking up/down/total to correctly shade deltas.
        self.commentW.setStyle(self.markStyle)
        self.commentW.changeMark(self.maxMark, self.score)
        # Make sure window is maximised.
        self.showMaximized()
        # Make sure window has min/max buttons.
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint
                            | Qt.WindowMinMaxButtonsHint)

        # Keyboard shortcuts.
        # Connect various key-presses to associated tool-button clicks
        # Allows us to translate a key-press into a button-press.
        # Key layout (mostly) matches tool-button layout
        self.keycodes = {
            # home-row
            Qt.Key_A: lambda: self.ui.zoomButton.animateClick(),
            Qt.Key_S: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_D: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_F: lambda: (self.commentW.currentItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_G: lambda: self.ui.textButton.animateClick(),
            # lower-row
            Qt.Key_Z: lambda: self.ui.moveButton.animateClick(),
            Qt.Key_X: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_C: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_V: lambda: (self.commentW.nextItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_B: lambda: self.ui.lineButton.animateClick(),
            # upper-row
            Qt.Key_Q: lambda: self.ui.panButton.animateClick(),
            Qt.Key_W: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_E: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_R: lambda: (self.commentW.previousItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_T: lambda: self.ui.penButton.animateClick(),

            # and then the same but for the left-handed
            # home-row
            Qt.Key_H: lambda: self.ui.textButton.animateClick(),
            Qt.Key_J: lambda: (self.commentW.currentItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_K: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_L: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_Semicolon: lambda: self.ui.zoomButton.animateClick(),
            # lower-row
            Qt.Key_N: lambda: self.ui.lineButton.animateClick(),
            Qt.Key_M: lambda: (self.commentW.nextItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_Comma: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_Period: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_Slash: lambda: self.ui.moveButton.animateClick(),
            # top-row
            Qt.Key_Y: lambda: self.ui.penButton.animateClick(),
            Qt.Key_U: lambda: (self.commentW.previousItem(),
                               self.commentW.CL.handleClick()),
            Qt.Key_I: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_O: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_P: lambda: self.ui.panButton.animateClick(),

            # Then maximize and mark buttons
            Qt.Key_Plus: lambda: self.swapMaxNorm(),
            Qt.Key_Backslash: lambda: self.swapMaxNorm(),
            Qt.Key_Minus: lambda: self.view.zoomOut(),
            Qt.Key_Equal: lambda: self.view.zoomIn(),
            # Only change-mark shortcuts 0-5.
            Qt.Key_QuoteLeft: lambda: self.keyToChangeMark(0),
            Qt.Key_0: lambda: self.keyToChangeMark(0),
            Qt.Key_1: lambda: self.keyToChangeMark(1),
            Qt.Key_2: lambda: self.keyToChangeMark(2),
            Qt.Key_3: lambda: self.keyToChangeMark(3),
            Qt.Key_4: lambda: self.keyToChangeMark(4),
            Qt.Key_5: lambda: self.keyToChangeMark(5),

            # ?-mark pop up a key-list
            Qt.Key_Question: lambda: self.keyPopUp(),

            # Toggle hide/unhide tools so as to maximise space for annotation
            Qt.Key_Home: lambda: self.toggleTools(),
        }

    def toggleTools(self):
        # Show / hide all the tools and so more space for the group-image
        # All tools in gui inside 'hideablebox' - so easily shown/hidden
        if self.ui.hideableBox.isHidden():
            self.ui.hideableBox.show()
            self.ui.hideButton.setText("Hide")
        else:
            self.ui.hideableBox.hide()
            self.ui.hideButton.setText("Reveal")

    def keyPopUp(self):
        # Pops up a little window which containts table of
        # keys and associated tools.
        keylist = {'a': 'Zoom', 's': 'Undo', 'd': 'Tick/QMark/Cross',
                   'f': 'Current Comment', 'g': 'Text', 'z': 'Move',
                   'x': 'Delete', 'c': 'Box/Whitebox', 'v': 'Next Comment',
                   'b': 'Line/Arrow', 'q': 'Pan',  'w': 'Redo',
                   'e': 'Cross/QMark/Tick', 'r': 'Previous Comment',
                   't': 'Pen/Highlighter', '+': 'Maximize Window',
                   '\\': 'Maximize Window', '-': 'Zoom Out', '=': 'Zoom In',
                   '`': 'Set Mark 0', '0': 'Set Mark 0', '1': 'Set Mark 1',
                   '2': 'Set Mark 2', '3': 'Set Mark 3', '4': 'Set Mark 4',
                   '5': 'Set Mark 5', ';': 'Zoom', 'l': 'Undo',
                   'k': 'Tick/QMark/Cross', 'j': 'Current Comment',
                   'h': 'Text', '/': 'Move', '.': 'Delete',
                   ',': 'Box/Whitebox', 'm': 'Next Comment', 'n': 'Line/Arrow',
                   'p': 'Pan', 'o': 'Redo', 'i': 'Cross/QMark/Tick',
                   'u': 'Previous Comment', 'y': 'Pen/Highlighter',
                   '?': 'Key Help'}
        # build KeyPress shortcuts dialog
        kp = QDialog()
        grid = QGridLayout()
        # Sortable table to display [key, description] pairs
        kt = QTableWidget()
        kt.setColumnCount(2)
        # Set headers - not editable.
        kt.setHorizontalHeaderLabels(['key', 'function'])
        kt.verticalHeader().hide()
        kt.setEditTriggers(QAbstractItemView.NoEditTriggers)
        kt.setSortingEnabled(True)
        # Read through the keys and put into table.
        for a in keylist.keys():
            r = kt.rowCount()
            kt.setRowCount(r+1)
            kt.setItem(r, 0, QTableWidgetItem(a))
            kt.setItem(r, 1, QTableWidgetItem("{}".format(keylist[a])))
        # Give it a close-button.
        cb = QPushButton("&close")
        cb.clicked.connect(kp.accept)
        grid.addWidget(kt, 1, 1, 3, 3)
        grid.addWidget(cb, 4, 3)
        kp.setLayout(grid)
        # Pop it up.
        kp.exec_()

    def setView(self):
        """Starts the pageview.
        The pageview (which is a qgraphicsview) which is (mostly) a layer
        between the annotation widget and the qgraphicsscene which
        actually stores all the graphics objects (the image, lines, boxes,
        text etc etc). The view allows us to zoom pan etc over image and
        its annotations.
        """
        # Start the pageview - pass it this widget (so it can communicate
        # back to us) and the filename of the image.
        self.view = PageView(self, self.imageFile)
        # put the view into the gui.
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)
        # set the initial view to contain the entire scene which at
        # this stage is just the image.
        self.view.fitInView(self.view.scene.sceneRect(),
                            Qt.KeepAspectRatioByExpanding)
        # Centre at top-left of image.
        self.view.centerOn(0, 0)

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def keyToChangeMark(self, buttonNumber):
        """Translates a key-press (0,1,2,3,4,5) into a button-press
        of the various delta-mark buttons in the mark-entry widget.
        If mark-up style then they trigger the positive mark buttons,
        hence p0,p1 etc... if mark down then triggers the negative mark
        buttons - n1,n2, etc.
        """
        if self.markHandler.style == 'Up':
            self.markHandler.markButtons[
                'p{}'.format(buttonNumber)].animateClick()
        elif self.markHandler.style == 'Down' and buttonNumber > 0:
            self.markHandler.markButtons[
                'm{}'.format(buttonNumber)].animateClick()

    def keyPressEvent(self, event):
        """Translates key-presses into tool-button presses if
        appropriate. Also captures the escape-key since this would
        normally close a qdialog.
        """
        # If a key-press detected use the keycodes dict to translate
        # the press into a function call (if exists)
        self.keycodes.get(event.key(), lambda *args: None)()
        # If escape key pressed then do not process it because
        # esc in a qdialog closes the window as a "reject".
        if event.key() != Qt.Key_Escape:
            super(Annotator, self).keyPressEvent(event)

    def setMode(self, newMode, newCursor):
        """Change the current tool mode.
        Changes the styling of the corresponding button, and
        also the cursor.
        """
        # Clear styling of the what was until now the current button
        if self.currentButton is None:
            pass
        else:
            self.currentButton.setStyleSheet("")
        # We change currentbutton to which ever widget sent us
        # to this function. We have to be a little careful since
        # not all widgets get the styling in the same way.
        # If the mark-handler widget sent us here, it takes care
        # of its own styling - so we update the little tool-tip
        # and set current button to none.
        if self.sender() == self.markHandler:
            self.setToolLine('delta')
            self.currentButton = None
        else:
            self.currentButton = self.sender()
            if self.currentButton == self.commentW.CL:
                self.setToolLine('comment')
                self.currentButton.setStyleSheet(
                    self.currentButtonStyleOutline)
            else:
                self.setToolLine(newMode)
                self.currentButton.setStyleSheet(
                    self.currentButtonStyleBackground)
            self.markHandler.clearButtonStyle()

        self.view.setMode(newMode)
        self.view.setCursor(newCursor)
        self.repaint()

    def setToolLine(self, newMode):
        self.ui.toolLineEdit.setText("{}".format(
            modeLines.get(newMode, newMode)))

    def setIcons(self):
        # pyinstaller creates a temp folder and stores path in _MEIPASS
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = "./icons"

        # tweak path for loading the icons for use with pyinstaller one-file.
        self.setIcon(self.ui.penButton, "pen", "{}/pen.svg".format(base_path))
        self.setIcon(self.ui.lineButton, "line",
                     "{}/line.svg".format(base_path))
        self.setIcon(self.ui.boxButton, "box",
                     "{}/rectangle.svg".format(base_path))
        self.setIcon(self.ui.textButton, "text",
                     "{}/text.svg".format(base_path))
        self.setIcon(self.ui.tickButton, "tick",
                     "{}/tick.svg".format(base_path))
        self.setIcon(self.ui.crossButton, "cross",
                     "{}/cross.svg".format(base_path))
        self.setIcon(self.ui.deleteButton, "delete",
                     "{}/delete.svg".format(base_path))
        self.setIcon(self.ui.moveButton, "move",
                     "{}/move.svg".format(base_path))
        self.setIcon(self.ui.zoomButton, "zoom",
                     "{}/zoom.svg".format(base_path))
        self.setIcon(self.ui.panButton, "pan",
                     "{}/pan.svg".format(base_path))
        self.setIcon(self.ui.undoButton, "undo",
                     "{}/undo.svg".format(base_path))
        self.setIcon(self.ui.redoButton, "redo",
                     "{}/redo.svg".format(base_path))
        self.setIcon(self.ui.commentButton, "com",
                     "{}/comment.svg".format(base_path))
        self.setIcon(self.ui.commentUpButton, "com up",
                     "{}/comment_up.svg".format(base_path))
        self.setIcon(self.ui.commentDownButton, "com dn",
                     "{}/comment_down.svg".format(base_path))

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
        self.ui.penButton.clicked.connect(
            lambda: self.setMode("pen", QCursor(Qt.ArrowCursor)))
        self.ui.lineButton.clicked.connect(
            lambda: self.setMode("line", QCursor(Qt.CrossCursor)))
        self.ui.boxButton.clicked.connect(
            lambda: self.setMode("box", QCursor(Qt.ArrowCursor)))
        self.ui.textButton.clicked.connect(
            lambda: self.setMode("text", QCursor(Qt.IBeamCursor)))
        self.ui.crossButton.clicked.connect(
            lambda: self.setMode("cross", QCursor(Qt.ArrowCursor)))
        self.ui.tickButton.clicked.connect(
            lambda: self.setMode("tick", QCursor(Qt.ArrowCursor)))
        self.ui.moveButton.clicked.connect(
            lambda: self.setMode("move", QCursor(Qt.OpenHandCursor)))
        self.ui.deleteButton.clicked.connect(
            lambda: self.setMode("delete", QCursor(Qt.ForbiddenCursor)))
        self.ui.zoomButton.clicked.connect(
            lambda: self.setMode("zoom", QCursor(Qt.SizeFDiagCursor)))
        self.ui.panButton.clicked.connect(
            lambda: (self.setMode("pan", QCursor(Qt.OpenHandCursor)),
                     self.view.setDragMode(1)))
        self.ui.undoButton.clicked.connect(self.view.undo)
        self.ui.redoButton.clicked.connect(self.view.redo)

        self.ui.keyHelpButton.clicked.connect(self.keyPopUp)

        self.ui.commentButton.clicked.connect(
            lambda: (self.commentW.currentItem(),
                     self.commentW.CL.handleClick()))
        self.ui.commentUpButton.clicked.connect(
            lambda: (self.commentW.previousItem(),
                     self.commentW.CL.handleClick()))
        self.ui.commentDownButton.clicked.connect(
            lambda: (self.commentW.nextItem(), self.commentW.CL.handleClick()))

        self.ui.finishedButton.clicked.connect(
            lambda: (self.commentW.saveComments(), self.closeEvent(True)))
        self.ui.finishNoRelaunchButton.clicked.connect(
            lambda: (self.commentW.saveComments(), self.closeEvent(False)))

        self.ui.cancelButton.clicked.connect(self.reject)

        self.commentW.CL.commentSignal.connect(self.handleComment)

        self.ui.hideButton.clicked.connect(self.toggleTools)

    def handleComment(self, dlt_txt):
        self.setMode("text", QCursor(Qt.IBeamCursor))
        # set the delta to 0 if it is out-of-bounds.
        delta = int(dlt_txt[0])
        if self.markStyle == 2:  # mark up - disable negative
            if delta <= 0 or delta + self.score > self.maxMark:
                self.view.makeComment(0, dlt_txt[1])
                return
        elif self.markStyle == 3:  # mark down - disable positive
            if delta >= 0 or delta + self.score < 0:
                self.view.makeComment(0, dlt_txt[1])
                return
        # Remaining possibility = mark total, enable all.
        self.view.makeComment(dlt_txt[0], dlt_txt[1])

    def setmarkHandler(self, markStyle):
        self.markHandler = MarkHandler(self.maxMark)
        self.ui.markGrid.addWidget(self.markHandler, 1, 1)
        self.markHandler.markSetSignal.connect(self.totalMarkSet)
        self.markHandler.deltaSetSignal.connect(self.deltaMarkSet)
        self.markHandler.setStyle(markStyle)
        if markStyle == 1:  # mark total style
            # don't connect the delta-tool to the changeMark function
            # this ensures that marked-comments do not change the total
            pass
        else:
            # connect the delta tool to the changeMark function.
            # delta and marked comments will change the total.
            self.view.scene.markChangedSignal.connect(self.changeMark)

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
        self.markHandler.setMark(self.score)
        self.markHandler.repaint()
        self.view.scene.scoreBox.changeScore(self.score)
        lookingAhead = self.score+dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.moveButton.animateClick()

    def closeEvent(self, relaunch):
        if type(relaunch) == QCloseEvent:
            self.launchAgain = False
            self.reject()
        else:
            # if marking total or up, be careful of giving 0-marks
            if self.score == 0 and self.markHandler.style != 'Down':
                msg = SimpleMessage('You have given 0 - please confirm')
                if msg.exec_() == QMessageBox.No:
                    return
            # if marking down, be careful of giving max-marks
            if self.score == self.maxMark and self.markHandler.style == 'Down':
                msg = SimpleMessage(
                    'You have given {} - please confirm'.format(self.maxMark))
                if msg.exec_() == QMessageBox.No:
                    return
            if relaunch:
                self.launchAgain = True
            else:
                self.launchAgain = False

            self.view.save()
            self.accept()
