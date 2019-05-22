__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai", "Matt Coles"]
__license__ = "GPLv3"

import sys

from PyQt5.QtCore import Qt, QSettings, QSize, pyqtSlot
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap, QCloseEvent
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
from useful_classes import CommentWidget, SimpleMessage, SimpleMessageCheckBox
from test_view import TestView
from uiFiles.ui_annotator_lhm import Ui_annotator_lhm
from uiFiles.ui_annotator_rhm import Ui_annotator_rhm

# Short descriptions of each tool to display to user.
modeLines = {
    "box": "L: highlighted box. R: opaque white box.",
    "comment": "L: paste comment and associated mark.",
    "cross": "L: cross. M: ?-mark. R: checkmark.",
    "delta": "L: paste mark. M: ?-mark. R: checkmark/cross.",
    "delete": "Delete object.",
    "line": "L: straight line. R: arrow.",
    "move": "Move object.",
    "pan": "Pan view.",
    "pen": "L: freehand pen. R: freehand highlighter.",
    "text": "Text. Enter: newline, Shift-Enter/ESC: finish.",
    "tick": "L: checkmark. M: ?-mark. R: cross.",
    "zoom": "L: Zoom in. R: zoom out.",
}


class Annotator(QDialog):
    """The main annotation window for annotating group-images
    and assigning marks.
    """

    def __init__(self, fname, maxMark, markStyle, mouseHand, parent=None):
        super(Annotator, self).__init__(parent)
        # remember parent
        self.parent = parent
        # Grab filename of image, max mark, mark style (total/up/down)
        # and mouse-hand (left/right)
        self.imageFile = fname
        self.maxMark = maxMark
        self.markStyle = markStyle
        # Show warnings or not
        self.markWarn = True
        self.commentWarn = True

        # a test view window - initially set to None
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
        # Set up the view of the group-image - loads in the image etc
        self.setView()
        # Create the comment list widget and put into gui.
        self.commentW = CommentWidget()
        self.ui.commentGrid.addWidget(self.commentW, 1, 1)
        # pass the marking style to the mark entry widget.
        # also when we set this up we have to connect various
        # mark set, delta-set, mark change signals to functions
        self.setMarkHandler(self.markStyle)
        # set alt-enter / alt-return as shortcut to finish annotating
        self.setEndShortCuts()
        # Set the tool icons
        self.setIcons()
        # Connect all the buttons to relevant functions
        self.setButtons()
        # Set up the score-box that gets stamped in top-left of image.
        # "k out of n" where k=current score, n = max score.
        self.view.scene.scoreBox.changeMax(self.maxMark)
        self.view.scene.scoreBox.changeScore(self.score)
        # pass this to the comment table too - it needs to know if we are
        # marking up/down/total to correctly shade deltas.
        self.commentW.setStyle(self.markStyle)
        self.commentW.changeMark(self.maxMark, self.score)
        # Make sure window has min/max buttons.
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint
        )
        # Make sure window is maximised.
        self.showMaximized()
        # Grab window settings from parent
        self.loadWindowSettings()

        # Keyboard shortcuts.
        # Connect various key-presses to associated tool-button clicks
        # Allows us to translate a key-press into a button-press.
        # Key layout (mostly) matches tool-button layout
        self.keycodes = {
            # home-row
            Qt.Key_A: lambda: self.ui.zoomButton.animateClick(),
            Qt.Key_S: lambda: self.ui.undoButton.animateClick(),
            Qt.Key_D: lambda: self.ui.tickButton.animateClick(),
            Qt.Key_F: lambda: (
                self.commentW.currentItem(),
                self.commentW.CL.handleClick(),
            ),
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
            Qt.Key_J: lambda: (
                self.commentW.currentItem(),
                self.commentW.CL.handleClick(),
            ),
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
            "c": "Box/Whitebox",
            "v": "Next Comment",
            "b": "Line/Arrow",
            "q": "Pan",
            "w": "Redo",
            "e": "Cross/QMark/Tick",
            "r": "Previous Comment",
            "t": "Pen/Highlighter",
            "+": "Maximize Window",
            "\\": "Maximize Window",
            "-": "Zoom Out",
            "=": "Zoom In",
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
            ",": "Box/Whitebox",
            "m": "Next Comment",
            "n": "Line/Arrow",
            "p": "Pan",
            "o": "Redo",
            "i": "Cross/QMark/Tick",
            "u": "Previous Comment",
            "y": "Pen/Highlighter",
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
        self.view.fitInView(self.view.scene.sceneRect(), Qt.KeepAspectRatioByExpanding)
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
        if self.markHandler.style == "Up":
            self.markHandler.markButtons["p{}".format(buttonNumber)].animateClick()
        elif self.markHandler.style == "Down" and buttonNumber > 0:
            self.markHandler.markButtons["m{}".format(buttonNumber)].animateClick()

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
            self.setToolLine("delta")
            # set button=none, since markHandler does its own styling
            self.currentButton = None
        else:
            # otherwise the button = whoever sent us here.
            self.currentButton = self.sender()
            # Set the style of that button - be careful of the
            # comment list - since it needs different styling
            if self.currentButton == self.commentW.CL:
                self.setToolLine("comment")
                self.currentButton.setStyleSheet(self.currentButtonStyleOutline)
            else:
                self.setToolLine(newMode)
                self.currentButton.setStyleSheet(self.currentButtonStyleBackground)
            # Clear the style of the mark-handler (this will mostly not do
            # anything, but saves us testing if we had styled it)
            self.markHandler.clearButtonStyle()
        # pass the new mode to the graphicsview
        self.view.setMode(newMode)
        # set the mouse cursor
        self.view.setCursor(newCursor)
        # refresh everything.
        self.repaint()

    def setToolLine(self, newMode):
        # sets the short help/description of the current tool
        self.ui.toolLineEdit.setText("{}".format(modeLines.get(newMode, newMode)))

    def setIcon(self, tb, txt, iconFile):
        # Helper command for setIcons - sets the text, loads the icon
        # and formats things nicely.
        tb.setText(txt)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        tb.setIcon(QIcon(QPixmap(iconFile)))
        tb.setIconSize(QSize(24, 24))
        tb.setMinimumWidth(60)

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

    def setEndShortCuts(self):
        # Set alt-enter or alt-return to end the annotator
        # The key-shortcuts fire a signal, which triggers the
        # endAndRelaunch slot.
        self.endShortCut = QShortcut(QKeySequence("Alt+Enter"), self)
        self.endShortCut.activated.connect(self.endAndRelaunch)
        self.endShortCutb = QShortcut(QKeySequence("Alt+Return"), self)
        self.endShortCutb.activated.connect(self.endAndRelaunch)

    # Simple mode change functions
    def boxMode(self):
        self.setMode("box", Qt.ArrowCursor)

    def crossMode(self):
        self.setMode("cross", Qt.ArrowCursor)

    def deleteMode(self):
        self.setMode("delete", Qt.ForbiddenCursor)

    def lineMode(self):
        self.setMode("line", Qt.CrossCursor)

    def moveMode(self):
        self.setMode("move", Qt.OpenHandCursor)

    def panMode(self):
        self.setMode("pan", Qt.OpenHandCursor)
        # The pan button also needs to change dragmode in the view
        self.view.setDragMode(1)

    def penMode(self):
        self.setMode("pen", Qt.ArrowCursor)

    def textMode(self):
        self.setMode("text", Qt.IBeamCursor)

    def tickMode(self):
        self.setMode("tick", Qt.ArrowCursor)

    def zoomMode(self):
        self.setMode("zoom", Qt.SizeFDiagCursor)

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
        self.ui.undoButton.clicked.connect(self.view.undo)
        self.ui.redoButton.clicked.connect(self.view.redo)
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
        self.setMode("text", QCursor(Qt.IBeamCursor))
        # Grab the delta from the arguments
        delta = int(dlt_txt[0])
        # We only paste the delta if it is appropriate - this depends on
        # the marking style.
        # If marking-up then keep delta if positive, and if applying it
        # will not push mark past maximium possible
        if self.markStyle == 2:  # mark up - disable negative
            if delta <= 0 or delta + self.score > self.maxMark:
                self.view.makeComment(0, dlt_txt[1])
                return
            else:
                self.view.makeComment(dlt_txt[0], dlt_txt[1])
                return
        # If marking down, then keep delta if negative, and if applying it
        # doesn't push mark down past zero.
        elif self.markStyle == 3:
            if delta >= 0 or delta + self.score < 0:
                self.view.makeComment(0, dlt_txt[1])
                return
            else:
                self.view.makeComment(dlt_txt[0], dlt_txt[1])
                return
        else:
            # Remaining possibility = mark total - no restrictions
            # since user has to set total mark manually - the deltas do not
            # change the mark.
            self.view.makeComment(dlt_txt[0], dlt_txt[1])
            return

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
        self.markHandler = MarkHandler(self.maxMark)
        self.ui.markGrid.addWidget(self.markHandler, 1, 1)
        # Connect the markHandler's mark-set and delta-set signals to
        # the appropriate functions here.
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
            # The view makes this signal when a delta is pasted
            self.view.scene.markChangedSignal.connect(self.changeMark)

    def totalMarkSet(self, tm):
        # Set the total mark and pass that info to the comment list
        # so it can shade over deltas that are no longer applicable.
        self.score = tm
        self.commentW.changeMark(self.maxMark, self.score)
        # also tell the scorebox in the top-left of the image what the
        # new total mark is.
        self.view.scene.scoreBox.changeScore(self.score)

    def deltaMarkSet(self, dm):
        """When a delta-mark button is clicked, or a comment selected
        the view (and scene) need to know what the current delta is so
        that it can be pasted in correctly (when user clicks on image).
        """
        # Compute mark if delta is applied = current mark + delta
        lookingAhead = self.score + dm
        # If it is out of range then change mode to "move" so that
        # the user cannot paste in that delta.
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.moveButton.animateClick()
            return
        # Otherwise set the mode and tell the view the current delta value.
        # which it, in turn, passes on to the pagescene.
        self.setMode("delta", QCursor(Qt.ArrowCursor))
        self.view.markDelta(dm)

    def changeMark(self, dm):
        """The mark has been changed by delta=dm. Update the mark-handler
        and the scorebox and check if the user can use this delta again
        while keeping the mark between 0 and the max possible.
        """
        # Update the current mark
        self.score += dm
        # Tell the mark-handler what the new mark is and force a repaint.
        self.markHandler.setMark(self.score)
        self.markHandler.repaint()
        # Tell the view (and scene) what the current mark is.
        self.view.scene.scoreBox.changeScore(self.score)
        # Look ahead to see if this delta can be used again while keeping
        # the mark within range. If not, then set mode to 'move'.
        lookingAhead = self.score + dm
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.ui.moveButton.animateClick()

    def closeEventRelaunch(self):
        self.closeEvent(True)

    def closeEventNoRelaunch(self):
        self.closeEvent(False)

    def loadWindowSettings(self):
        if self.parent.annotatorSettings.value("geometry") is not None:
            self.restoreGeometry(self.parent.annotatorSettings.value("geometry"))
        if self.parent.annotatorSettings.value("markWarnings") is not None:
            self.markWarn = self.parent.annotatorSettings.value("markWarnings")
        if self.parent.annotatorSettings.value("commentWarnings") is not None:
            self.commentWarn = self.parent.annotatorSettings.value("commentWarnings")

    def saveWindowSettings(self):
        self.parent.annotatorSettings.setValue("geometry", self.saveGeometry())
        self.parent.annotatorSettings.setValue("markWarnings", self.markWarn)
        self.parent.annotatorSettings.setValue("commentWarnings", self.commentWarn)

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
        else:
            # check if comments have been left.
            if self.view.countComments() == 0:
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
            # Save the view/scene to file.
            self.view.save()
            # Save the comments
            self.view.saveComments()
            # Save the window settings
            self.saveWindowSettings()
            # Close the annotator(QDialog) with an 'accept'.
            self.accept()
