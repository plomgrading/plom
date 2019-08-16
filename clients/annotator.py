__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json
import os
import sys

from PyQt5.QtCore import Qt, QSettings, QSize, QTimer, pyqtSlot
from PyQt5.QtGui import (
    QCursor,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPixmap,
    QCloseEvent,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QGridLayout,
)

from mark_handler import MarkHandler
from pageview import PageView
from pagescene import PageScene

from useful_classes import (
    CommentWidget,
    ErrorMessage,
    SimpleMessage,
    SimpleMessageCheckBox,
)
from test_view import TestView
from uiFiles.ui_annotator_lhm import Ui_annotator_lhm
from uiFiles.ui_annotator_rhm import Ui_annotator_rhm

# Short descriptions of each tool to display to user.
tipText = {
    "box": "Box: L = highlighted box, R/Shift = highlighted ellipse.",
    "com": "Comment: L = paste comment and associated mark.",
    "com up": "Comment up: Select previous comment in list",
    "com down": "Comment down: Select next comment in list",
    "cross": "Cross: L = cross, M/Ctrl = ?-mark, R/Shift = checkmark.",
    "delta": "Delta: L = paste mark, M/Ctrl = ?-mark, R/Shift = checkmark/cross.",
    "delete": "Delete: L = Delete object, L-drag = delete area.",
    "line": "Line: L = straight line, M/Ctrl = double-arrow, R/Shift = arrow.",
    "move": "Move object.",
    "pan": "Pan view.",
    "pen": "Pen: L = freehand pen, M/Ctrl = pen with arrows, R/Shift = freehand highlighter.",
    "redo": "Redo: Redo last action",
    "text": "Text: Enter = newline, Shift-Enter/ESC = finish.",
    "tick": "Tick: L = checkmark, M/Ctrl = ?-mark, R/Shift = cross.",
    "undo": "Undo: Undo last action",
    "zoom": "Zoom: L = Zoom in, R = zoom out.",
}


class Annotator(QDialog):
    """The main annotation window for annotating group-images
    and assigning marks.
    """

    def __init__(
        self, fname, maxMark, markStyle, mouseHand, parent=None, plomDict=None
    ):
        super(Annotator, self).__init__(parent)
        # remember parent
        self.parent = parent
        # Grab filename of image, max mark, mark style (total/up/down)
        # and mouse-hand (left/right)
        self.imageFile = fname
        self.maxMark = maxMark
        # get markstyle from plomDict
        if plomDict is None:
            self.markStyle = markStyle
        else:
            self.markStyle = plomDict["markStyle"]

        # Show warnings or not
        self.markWarn = True
        self.commentWarn = True

        # a test view pop-up window - initially set to None
        # for viewing whole paper
        self.testView = None
        # Set current mark to 0.
        self.score = 0
        # make styling of currently selected button/tool.
        self.currentButtonStyleBackground = (
            "border: 2px solid #00aaaa; "
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop: 0 #00dddd, stop: 1 #00aaaa);"
        )
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

        # Set up the graphicsview and graphicsscene of the group-image
        # loads in the image etc
        self.view = None
        self.scene = None
        self.setViewAndScene()

        # Create the comment list widget and put into gui.
        self.commentW = CommentWidget(self, self.maxMark)
        self.ui.commentGrid.addWidget(self.commentW, 1, 1)
        # pass the marking style to the mark entry widget.
        # also when we set this up we have to connect various
        # mark set, delta-set, mark change functions
        self.setMarkHandler(self.markStyle)
        # set alt-enter / alt-return as shortcut to finish annotating
        # also set ctrl-n and ctrl-b as same shortcut.
        # set ctrl-+ as zoom toggle shortcut
        # set ctrl-z / ctrl-y as undo/redo shortcuts
        self.setMiscShortCuts()

        # set the zoom combobox
        self.setZoomComboBox()
        # Set the tool icons
        self.setIcons()
        # Set up cursors
        self.loadCursors()

        # Connect all the buttons to relevant functions
        self.setButtons()
        # pass this to the comment table too - it needs to know if we are
        # marking up/down/total to correctly shade deltas.
        self.commentW.setStyle(self.markStyle)
        self.commentW.changeMark(self.score)
        # Make sure window has min/max buttons.
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint
        )
        # Make sure window is maximised.
        self.showMaximized()
        # Grab window settings from parent
        self.loadWindowSettings()

        # Keyboard shortcuts.
        self.keycodes = self.getKeyCodes()

        # Connect various key-presses to associated tool-button clicks
        # Allows us to translate a key-press into a button-press.
        # Key layout (mostly) matches tool-button layout
        # Very last thing = unpickle scene from plomDict
        if plomDict is not None:
            self.unpickleIt(plomDict)

    def loadCursors(self):
        # https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
        # pyinstaller creates a temp folder and stores path in _MEIPASS
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = "./cursors"

        # load pixmaps for cursors and set the hotspots
        self.cursorBox = QCursor(QPixmap("{}/box.png".format(base_path)), 4, 4)
        self.cursorCross = QCursor(QPixmap("{}/cross.png".format(base_path)), 4, 4)
        self.cursorDelete = QCursor(QPixmap("{}/delete.png".format(base_path)), 4, 4)
        self.cursorLine = QCursor(QPixmap("{}/line.png".format(base_path)), 4, 4)
        self.cursorPen = QCursor(QPixmap("{}/pen.png".format(base_path)), 4, 4)
        self.cursorTick = QCursor(QPixmap("{}/tick.png".format(base_path)), 4, 4)

    def getKeyCodes(self):
        return {
            # home-row
            Qt.Key_A: lambda: self.ui.zoomButton.animateClick(),
            Qt.Key_S: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_D: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_F: lambda: self.commentMode(),
            Qt.Key_G: lambda: self.ui.textButton.animateClick(),
            # lower-row
            Qt.Key_Z: lambda: self.ui.moveButton.animateClick(),
            Qt.Key_X: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_C: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_V: lambda: (
                self.commentW.nextItem(),
                self.commentW.CL.handleClick(),
            ),
            Qt.Key_B: lambda: self.ui.lineButton.animateClick(),
            # upper-row
            Qt.Key_Q: lambda: self.ui.panButton.animateClick(),
            Qt.Key_W: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_E: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_R: lambda: (
                self.commentW.previousItem(),
                self.commentW.CL.handleClick(),
            ),
            Qt.Key_T: lambda: self.ui.penButton.animateClick(),
            # and then the same but for the left-handed
            # home-row
            Qt.Key_H: lambda: self.ui.textButton.animateClick(),
            Qt.Key_J: lambda: self.commentMode(),
            Qt.Key_K: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_L: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_Semicolon: lambda: self.ui.zoomButton.animateClick(),
            # lower-row
            Qt.Key_N: lambda: self.ui.lineButton.animateClick(),
            Qt.Key_M: lambda: (
                self.commentW.nextItem(),
                self.commentW.CL.handleClick(),
            ),
            Qt.Key_Comma: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_Period: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_Slash: lambda: self.ui.moveButton.animateClick(),
            # top-row
            Qt.Key_Y: lambda: self.ui.penButton.animateClick(),
            Qt.Key_U: lambda: (
                self.commentW.previousItem(),
                self.commentW.CL.handleClick(),
            ),
            Qt.Key_I: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_O: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_P: lambda: self.ui.panButton.animateClick(),
            # Then maximize and mark buttons
            Qt.Key_Backslash: lambda: self.swapMaxNorm(),
            Qt.Key_Plus: lambda: self.view.zoomIn(),
            Qt.Key_Equal: lambda: self.view.zoomIn(),
            Qt.Key_Minus: lambda: self.view.zoomOut(),
            Qt.Key_Underscore: lambda: self.view.zoomOut(),
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
            # view whole paper
            Qt.Key_F1: lambda: self.viewWholePaper(),
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

    def viewWholePaper(self):
        files = self.parent.viewWholePaper()
        if self.testView is None:
            self.testView = TestView(self, files)

    def doneViewingPaper(self):
        self.testView = None
        self.parent.doneWithViewFiles()

    def keyPopUp(self):
        # Pops up a little window which containts table of
        # keys and associated tools.
        keylist = {
            "a": "Zoom",
            "s": "Undo",
            "d": "Tick/QMark/Cross",
            "f": "Current Comment",
            "g": "Text",
            "z": "Move",
            "x": "Delete",
            "c": "Box/Ellipse",
            "v": "Next Comment",
            "b": "Line/DoubleArrow/Arrow",
            "q": "Pan",
            "w": "Redo",
            "e": "Cross/QMark/Tick",
            "r": "Previous Comment",
            "t": "Pen/DoubleArrow/Highlighter",
            "\\": "Maximize Window",
            "-": "Zoom Out",
            "_": "Zoom Out",
            "+": "Zoom In",
            "=": "Zoom In",
            "ctrl-=": "Toggle Zoom",
            "`": "Set Mark 0",
            "0": "Set Mark 0",
            "1": "Set Mark 1",
            "2": "Set Mark 2",
            "3": "Set Mark 3",
            "4": "Set Mark 4",
            "5": "Set Mark 5",
            ";": "Zoom",
            "l": "Undo",
            "k": "Tick/QMark/Cross",
            "j": "Current Comment",
            "h": "Text",
            "/": "Move",
            ".": "Delete",
            ",": "Box/Ellipse",
            "m": "Next Comment",
            "n": "Line/DoubleArrow/Arrow",
            "p": "Pan",
            "o": "Redo",
            "i": "Cross/QMark/Tick",
            "u": "Previous Comment",
            "y": "Pen/DoubleArrow/Highlighter",
            "f1": "View whole paper (may be fn-f1 depending on your system)",
            "?": "Key Help",
        }
        # build KeyPress shortcuts dialog
        kp = QDialog()
        grid = QGridLayout()
        # Sortable table to display [key, description] pairs
        kt = QTableWidget()
        kt.setColumnCount(2)
        # Set headers - not editable.
        kt.setHorizontalHeaderLabels(["key", "function"])
        kt.verticalHeader().hide()
        kt.setEditTriggers(QAbstractItemView.NoEditTriggers)
        kt.setSortingEnabled(True)
        # Read through the keys and put into table.
        for a in keylist.keys():
            r = kt.rowCount()
            kt.setRowCount(r + 1)
            kt.setItem(r, 0, QTableWidgetItem(a))
            kt.setItem(r, 1, QTableWidgetItem("{}".format(keylist[a])))
        # Give it a close-button.
        cb = QPushButton("&close")
        cb.clicked.connect(kp.accept)
        grid.addWidget(kt, 1, 1, 3, 3)
        grid.addWidget(cb, 4, 3)
        kp.setLayout(grid)
        # Resize items to fit
        kt.resizeColumnsToContents()
        kt.resizeRowsToContents()
        # Pop it up.
        kp.exec_()

    def setViewAndScene(self):
        """Starts the pageview.
        The pageview (which is a qgraphicsview) which is (mostly) a layer
        between the annotation widget and the qgraphicsscene which
        actually stores all the graphics objects (the image, lines, boxes,
        text etc etc). The view allows us to zoom pan etc over image and
        its annotations.
        """
        # Start the pageview - pass it this widget (so it can communicate
        # back to us) and the filename of the image.
        self.view = PageView(self)
        self.scene = PageScene(
            self, self.imageFile, self.maxMark, self.score, self.markStyle
        )
        # connect view to scene
        self.view.connectScene(self.scene)
        # scene knows which views are connected via self.views()

        # put the view into the gui.
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)
        # set the initial view to contain the entire scene which at
        # this stage is just the image.
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatioByExpanding)
        # Centre at top-left of image.
        self.view.centerOn(0, 0)
        # click the move button
        self.ui.moveButton.animateClick()

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
        if self.markHandler.style == "Up":
            self.markHandler.markButtons["p{}".format(buttonNumber)].animateClick()
        elif self.markHandler.style == "Down" and buttonNumber > 0:
            self.markHandler.markButtons["m{}".format(buttonNumber)].animateClick()

    def keyPressEvent(self, event):
        """Translates key-presses into tool-button presses if
        appropriate. Also captures the escape-key since this would
        normally close a qdialog.
        """
        # Check to see if no mousebutton pressed
        # If a key-press detected use the keycodes dict to translate
        # the press into a function call (if exists)
        if QGuiApplication.mouseButtons() == Qt.NoButton:
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
        if self.currentButton is not None:
            self.currentButton.setStyleSheet("")

        # We change currentbutton to which ever widget sent us
        # to this function. We have to be a little careful since
        # not all widgets get the styling in the same way.
        # If the mark-handler widget sent us here, it takes care
        # of its own styling - so we update the little tool-tip
        # and set current button to none.
        if isinstance(self.sender(), QPushButton):
            # has come from mark-change button in handler, so
            # set button=none, since markHandler does its own styling
            self.currentButton = None
        else:
            # Clear the style of the mark-handler (this will mostly not do
            # anything, but saves us testing if we had styled it)
            self.markHandler.clearButtonStyle()
            # the current button = whoever sent us here.
            self.currentButton = self.sender()
            # Set the style of that button - be careful of the
            # comment list - since it needs different styling
            if self.currentButton == self.commentW.CL:
                self.currentButton.setStyleSheet(self.currentButtonStyleOutline)
                self.ui.commentButton.setStyleSheet(self.currentButtonStyleBackground)
            else:
                self.currentButton.setStyleSheet(self.currentButtonStyleBackground)
                # make sure comment button style is cleared
                self.ui.commentButton.setStyleSheet("")
        # pass the new mode to the graphicsview, and set the cursor in view
        self.scene.setMode(newMode)
        self.view.setCursor(newCursor)
        # refresh everything.
        self.repaint()

    def setIcon(self, tb, txt, iconFile):
        # Helper command for setIcons - sets the tooltip, loads the icon
        # and formats things nicely.
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.setToolTip("{}".format(tipText.get(txt, txt)))
        tb.setIcon(QIcon(QPixmap(iconFile)))
        tb.setIconSize(QSize(40, 40))

    def setIcons(self):
        """Set up the icons for the tools.
        A little care because of where a pyinstaller-built executable
        stores them.
        """
        # https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
        # pyinstaller creates a temp folder and stores path in _MEIPASS
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = "./icons"

        self.setIcon(self.ui.boxButton, "box", "{}/rectangle.svg".format(base_path))
        self.setIcon(self.ui.commentButton, "com", "{}/comment.svg".format(base_path))
        self.setIcon(
            self.ui.commentDownButton, "com dn", "{}/comment_down.svg".format(base_path)
        )
        self.setIcon(
            self.ui.commentUpButton, "com up", "{}/comment_up.svg".format(base_path)
        )
        self.setIcon(self.ui.crossButton, "cross", "{}/cross.svg".format(base_path))
        self.setIcon(self.ui.deleteButton, "delete", "{}/delete.svg".format(base_path))
        self.setIcon(self.ui.lineButton, "line", "{}/line.svg".format(base_path))
        self.setIcon(self.ui.moveButton, "move", "{}/move.svg".format(base_path))
        self.setIcon(self.ui.panButton, "pan", "{}/pan.svg".format(base_path))
        self.setIcon(self.ui.penButton, "pen", "{}/pen.svg".format(base_path))
        self.setIcon(self.ui.redoButton, "redo", "{}/redo.svg".format(base_path))
        self.setIcon(self.ui.textButton, "text", "{}/text.svg".format(base_path))
        self.setIcon(self.ui.tickButton, "tick", "{}/tick.svg".format(base_path))
        self.setIcon(self.ui.undoButton, "undo", "{}/undo.svg".format(base_path))
        self.setIcon(self.ui.zoomButton, "zoom", "{}/zoom.svg".format(base_path))

    # The 'endAndRelaunch' slot - this saves the comment-list, closes
    # the annotator. The marker window then asks the server for the next
    # unmarked image and fires up the annotator on that.
    @pyqtSlot()
    def endAndRelaunch(self):
        self.commentW.saveComments()
        self.closeEvent(True)

    def setMiscShortCuts(self):
        # Set alt-enter or alt-return to end the annotator
        # The key-shortcuts fire a signal, which triggers the
        # endAndRelaunch slot.
        self.endShortCut = QShortcut(QKeySequence("Alt+Enter"), self)
        self.endShortCut.activated.connect(self.endAndRelaunch)
        self.endShortCutb = QShortcut(QKeySequence("Alt+Return"), self)
        self.endShortCutb.activated.connect(self.endAndRelaunch)
        # shortcuts for next paper
        self.endShortCutc = QShortcut(QKeySequence("Ctrl+n"), self)
        self.endShortCutc.activated.connect(self.endAndRelaunch)
        self.endShortCutd = QShortcut(QKeySequence("Ctrl+b"), self)
        self.endShortCutd.activated.connect(self.endAndRelaunch)
        # shortcuts for zoom-states
        self.zoomToggleShortCut = QShortcut(QKeySequence("Ctrl+="), self)
        self.zoomToggleShortCut.activated.connect(self.view.zoomToggle)
        # shortcuts for undo/redo
        self.undoShortCut = QShortcut(QKeySequence("Ctrl+z"), self)
        self.undoShortCut.activated.connect(self.scene.undo)
        self.redoShortCut = QShortcut(QKeySequence("Ctrl+y"), self)
        self.redoShortCut.activated.connect(self.scene.redo)

    # Simple mode change functions
    def boxMode(self):
        self.setMode("box", self.cursorBox)

    def commentMode(self):
        if self.currentButton == self.commentW.CL:
            self.commentW.nextItem()
        else:
            self.commentW.currentItem()
        self.commentW.CL.handleClick()

    def crossMode(self):
        self.setMode("cross", self.cursorCross)

    def deleteMode(self):
        self.setMode("delete", self.cursorDelete)

    def lineMode(self):
        self.setMode("line", self.cursorLine)

    def moveMode(self):
        self.setMode("move", Qt.OpenHandCursor)

    def panMode(self):
        self.setMode("pan", Qt.OpenHandCursor)
        # The pan button also needs to change dragmode in the view
        self.view.setDragMode(1)

    def penMode(self):
        self.setMode("pen", self.cursorPen)

    def textMode(self):
        self.setMode("text", Qt.IBeamCursor)

    def tickMode(self):
        self.setMode("tick", self.cursorTick)

    def zoomMode(self):
        self.setMode("zoom", Qt.SizeFDiagCursor)

    def loadModeFromBefore(self, mode, aux=None):
        self.loadModes = {
            "box": lambda: self.ui.boxButton.animateClick(),
            "comment": lambda: self.commentMode(),
            "cross": lambda: self.ui.crossButton.animateClick(),
            "line": lambda: self.ui.lineButton.animateClick(),
            "pen": lambda: self.ui.penButton.animateClick(),
            "text": lambda: self.ui.textButton.animateClick(),
            "tick": lambda: self.ui.tickButton.animateClick(),
        }
        if mode == "delta" and aux is not None:
            self.markHandler.loadDeltaValue(aux)
        elif mode == "comment" and aux is not None:
            self.commentW.setCurrentItemRow(aux)
            self.ui.commentButton.animateClick()
        else:
            self.loadModes.get(mode, lambda *args: None)()

    def setButtons(self):
        """Connect buttons to functions.
        """
        # List of tool buttons, the corresponding modes and cursor shapes
        self.ui.boxButton.clicked.connect(self.boxMode)
        self.ui.crossButton.clicked.connect(self.crossMode)
        self.ui.deleteButton.clicked.connect(self.deleteMode)
        self.ui.lineButton.clicked.connect(self.lineMode)
        self.ui.moveButton.clicked.connect(self.moveMode)
        self.ui.panButton.clicked.connect(self.panMode)
        self.ui.penButton.clicked.connect(self.penMode)
        self.ui.textButton.clicked.connect(self.textMode)
        self.ui.tickButton.clicked.connect(self.tickMode)
        self.ui.zoomButton.clicked.connect(self.zoomMode)

        # Pass the undo/redo button clicks on to the view
        self.ui.undoButton.clicked.connect(self.scene.undo)
        self.ui.redoButton.clicked.connect(self.scene.redo)
        # The key-help button connects to the keyPopUp command.
        self.ui.keyHelpButton.clicked.connect(self.keyPopUp)
        # Cancel button closes annotator(QDialog) with a 'reject'
        self.ui.cancelButton.clicked.connect(self.reject)
        # Hide button connects to the toggleTools command
        self.ui.hideButton.clicked.connect(self.toggleTools)

        # Connect the comment buttons to the comment list
        # They select the item and trigger its handleClick which fires
        # off a commentSignal which will be picked up by the annotator
        # First up connect the comment list's signal to the annotator's
        # handle comment function.
        self.commentW.CL.commentSignal.connect(self.handleComment)
        # Now connect up the buttons
        self.ui.commentButton.clicked.connect(self.commentW.currentItem)
        self.ui.commentButton.clicked.connect(self.commentW.CL.handleClick)
        # the previous comment button
        self.ui.commentUpButton.clicked.connect(self.commentW.previousItem)
        self.ui.commentUpButton.clicked.connect(self.commentW.CL.handleClick)
        # the next comment button
        self.ui.commentDownButton.clicked.connect(self.commentW.nextItem)
        self.ui.commentDownButton.clicked.connect(self.commentW.CL.handleClick)
        # Connect up the finishing buttons
        self.ui.finishedButton.clicked.connect(self.commentW.saveComments)
        self.ui.finishedButton.clicked.connect(self.closeEventRelaunch)
        self.ui.finishNoRelaunchButton.clicked.connect(self.commentW.saveComments)
        self.ui.finishNoRelaunchButton.clicked.connect(self.closeEventNoRelaunch)

    def handleComment(self, dlt_txt):
        """When the user selects a comment this function will be triggered.
        The function is passed dlt_txt = [delta, comment text].
        It sets the mode to text, but also passes the comment's text and
        value (ie +/- n marks) to the pageview - which in turn tells the
        pagescene. The scene's mode will be set to 'comment' so that when
        the user clicks there the delta+comment items are created and
        then pasted into place.
        """
        # Set the model to text and change cursor.
        # self.setMode("comment", self.cursorComment)
        self.setMode("comment", QCursor(Qt.IBeamCursor))
        # Grab the delta from the arguments
        self.scene.changeTheComment(dlt_txt[0], dlt_txt[1], annotatorUpdate=True)

    def setMarkHandler(self, markStyle):
        """Set up the mark handling widget inside the annotator gui.
        Can be one of 3 styles - mark up, down or total.
        Also connect the handler's signals - when the mark is set,
        or delta-mark set to appropriate functions in the annotator.
        Also - to set up the mark-delta correctly - the view has to
        signal back to the annotator when a delta is pasted onto the
        image.
        """
        # Build the mark handler and put into the gui.
        self.markHandler = MarkHandler(self, self.maxMark)
        self.markHandler.setStyle(markStyle)
        self.ui.markGrid.addWidget(self.markHandler, 1, 1)

    def totalMarkSet(self, tm):
        # Set the total mark and pass that info to the comment list
        # so it can shade over deltas that are no longer applicable.
        self.score = tm
        self.commentW.changeMark(self.score)
        # also tell the scene what the new mark is
        self.scene.setTheMark(self.score)

    def deltaMarkSet(self, dm):
        """When a delta-mark button is clicked, or a comment selected
        the view (and scene) need to know what the current delta is so
        that it can be pasted in correctly (when user clicks on image).
        """
        # Change the mode to delta
        self.setMode("delta", QCursor(Qt.IBeamCursor))
        # Try changing the delta in the scene
        if not self.scene.changeTheDelta(dm, annotatorUpdate=True):
            # If it is out of range then change mode to "move" so that
            # the user cannot paste in that delta.
            self.ui.moveButton.animateClick()
            return

    def changeMark(self, score):
        """The mark has been changed. Update the mark-handler.
        """
        # Tell the mark-handler what the new mark is and force a repaint.
        assert self.markStyle != 1, "Should not be called if mark-total"

        self.score = score
        self.markHandler.setMark(self.score)
        self.markHandler.repaint()

    def closeEventRelaunch(self):
        self.closeEvent(True)

    def closeEventNoRelaunch(self):
        self.closeEvent(False)

    def loadWindowSettings(self):
        if self.parent.annotatorSettings["geometry"] is not None:
            self.restoreGeometry(self.parent.annotatorSettings["geometry"])
        if self.parent.annotatorSettings["markWarnings"] is not None:
            self.markWarn = self.parent.annotatorSettings["markWarnings"]
        if self.parent.annotatorSettings["commentWarnings"] is not None:
            self.commentWarn = self.parent.annotatorSettings["commentWarnings"]
        if self.parent.annotatorSettings["tool"] is not None:
            if self.parent.annotatorSettings["tool"] == "delta":
                dlt = self.parent.annotatorSettings["delta"]
                self.loadModeFromBefore("delta", dlt)
            elif self.parent.annotatorSettings["tool"] == "comment":
                cmt = self.parent.annotatorSettings["comment"]
                self.loadModeFromBefore("comment", cmt)
            else:
                self.loadModeFromBefore(self.parent.annotatorSettings["tool"])

        if self.parent.annotatorSettings["viewRectangle"] is not None:
            # put in slight delay so that any resize events are done.
            QTimer.singleShot(
                150,
                lambda: self.view.initialZoom(
                    self.parent.annotatorSettings["viewRectangle"]
                ),
            )
        else:
            QTimer.singleShot(150, lambda: self.view.initialZoom(None))
        # there is some redundancy between the above and the below.
        if self.parent.annotatorSettings["zoomState"] is not None:
            # put in slight delay so that any resize events are done.
            QTimer.singleShot(
                200,
                lambda: self.ui.zoomCB.setCurrentIndex(
                    self.parent.annotatorSettings["zoomState"]
                ),
            )
        else:
            QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(1))

    def saveWindowSettings(self):
        self.parent.annotatorSettings["geometry"] = self.saveGeometry()
        self.parent.annotatorSettings["markWarnings"] = self.markWarn
        self.parent.annotatorSettings["commentWarnings"] = self.commentWarn
        self.parent.annotatorSettings["viewRectangle"] = self.view.vrect
        self.parent.annotatorSettings["zoomState"] = self.ui.zoomCB.currentIndex()
        self.parent.annotatorSettings["tool"] = self.scene.mode
        if self.scene.mode == "delta":
            self.parent.annotatorSettings["delta"] = self.scene.markDelta
        if self.scene.mode == "comment":
            self.parent.annotatorSettings["comment"] = self.commentW.getCurrentItemRow()

    def closeEvent(self, relaunch):
        """When the user closes the window - either by clicking on the
        little standard all windows have them close icon in the titlebar
        or by clicking on 'finished' - do some basic checks.
        If the titlebar close has been clicked then we assume the user
        is cancelling the annotations.
        Otherwise - we assume they want to accept them. Simple sanity check
        that user meant to close the window.
        Be careful of a score of 0 - when mark total or mark up.
        Be careful of max-score when marking down.
        In either case - get user to confirm the score before closing.
        """
        # Save the current window settings for next time annotator is launched
        self.saveWindowSettings()

        # If the titlebar close clicked then don't relauch and close the
        # annotator (QDialog) with a 'reject'
        if type(relaunch) == QCloseEvent:
            self.launchAgain = False
            self.reject()
        # do some checks before accepting things
        if not self.scene.areThereAnnotations():
            msg = ErrorMessage("Please make an annotation, even if the page is blank.")
            msg.exec_()
            return

        # check if comments have been left.
        if self.scene.countComments() == 0:
            # error message if total is not 0 or full
            if self.score > 0 and self.score < self.maxMark and self.commentWarn:
                msg = SimpleMessageCheckBox(
                    "You have given no comments.\n Please confirm."
                )
                if msg.exec_() == QMessageBox.No:
                    return
                if msg.cb.checkState() == Qt.Checked:
                    self.commentWarn = False

        # if marking total or up, be careful when giving 0-marks
        if self.score == 0 and self.markHandler.style != "Down" and self.markWarn:
            msg = SimpleMessageCheckBox("You have given 0 - please confirm")
            if msg.exec_() == QMessageBox.No:
                return
            if msg.cb.checkState() == Qt.Checked:
                self.markWarn = False
        # if marking down, be careful of giving max-marks
        if (
            self.score == self.maxMark
            and self.markHandler.style == "Down"
            and self.markWarn
        ):
            msg = SimpleMessageCheckBox(
                "You have given {} - please confirm".format(self.maxMark)
            )
            if msg.exec_() == QMessageBox.No:
                return
            if msg.cb.checkState() == Qt.Checked:
                self.markWarn = False
        if relaunch:
            self.launchAgain = True
        else:
            self.launchAgain = False

        if not self.checkAllObjectsInside():
            return

        # Save the scene to file.
        self.scene.save()
        # Save the marker's comments
        self.saveMarkerComments()
        # Pickle the scene as a plom-file
        self.pickleIt()
        # Save the window settings
        self.saveWindowSettings()
        # Close the annotator(QDialog) with an 'accept'.
        self.accept()

    def checkAllObjectsInside(self):
        if self.scene.checkAllObjectsInside():
            return True
        else:
            # some objects outside the image, check if user really wants to finish
            msg = SimpleMessage(
                "Some annotations outside pageimage. Do you really want to finish?"
            )
            if msg.exec_() == QMessageBox.No:
                return False
            else:
                return True

    def getComments(self):
        return self.scene.getComments()

    def saveMarkerComments(self):
        commentList = self.getComments()
        # image file is <blah>.png, save comments as <blah>.json
        with open(self.imageFile[:-3] + "json", "w") as commentFile:
            json.dump(commentList, commentFile)

    def latexAFragment(self, txt):
        return self.parent.latexAFragment(txt)

    def pickleIt(self):
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        plomDict = {
            "fileName": os.path.basename(self.imageFile),
            "markStyle": self.markStyle,
            "maxMark": self.maxMark,
            "currentMark": self.score,
            "sceneItems": lst,
        }
        # save pickled file as <blah>.plom
        plomFile = self.imageFile[:-3] + "plom"
        with open(plomFile, "w") as fh:
            json.dump(plomDict, fh)

    def unpickleIt(self, plomDict):
        self.view.setHidden(True)
        self.scene.unpickleSceneItems(plomDict["sceneItems"])
        # if markstyle is "Total", then click appropriate button
        if self.markStyle == 1:
            self.markHandler.unpickleTotal(plomDict["currentMark"])
        self.view.setHidden(False)

    def setZoomComboBox(self):
        self.ui.zoomCB.addItem("User")
        self.ui.zoomCB.addItem("Fit Page")
        self.ui.zoomCB.addItem("Fit Width")
        self.ui.zoomCB.addItem("Fit Height")
        self.ui.zoomCB.addItem("200%")
        self.ui.zoomCB.addItem("150%")
        self.ui.zoomCB.addItem("100%")
        self.ui.zoomCB.addItem("50%")
        self.ui.zoomCB.addItem("33%")
        self.ui.zoomCB.currentIndexChanged.connect(self.zoomCBChanged)

    def changeCBZoom(self, v):
        old = self.ui.zoomCB.blockSignals(True)
        self.ui.zoomCB.setCurrentIndex(v)
        self.ui.zoomCB.blockSignals(old)

    def zoomCBChanged(self):
        if self.ui.zoomCB.currentText() == "Fit Page":
            self.view.zoomAll()
        elif self.ui.zoomCB.currentText() == "Fit Width":
            self.view.zoomWidth()
        elif self.ui.zoomCB.currentText() == "Fit Height":
            self.view.zoomHeight()
        elif self.ui.zoomCB.currentText() == "100%":
            self.view.zoomReset(1)
        elif self.ui.zoomCB.currentText() == "150%":
            self.view.zoomReset(1.5)
        elif self.ui.zoomCB.currentText() == "200%":
            self.view.zoomReset(2)
        elif self.ui.zoomCB.currentText() == "50%":
            self.view.zoomReset(0.5)
        elif self.ui.zoomCB.currentText() == "33%":
            self.view.zoomReset(0.33)
        else:
            pass
        self.view.setFocus()
