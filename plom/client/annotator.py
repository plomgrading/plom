__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json
import os
import sys
import logging
import pkg_resources

from PyQt5.QtCore import (
    Qt,
    QByteArray,
    QRectF,
    QSettings,
    QSize,
    QTimer,
    QElapsedTimer,
    pyqtSlot,
    pyqtSignal,
)
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
    QAction,
    QDialog,
    QWidget,
    QMainWindow,
    QGridLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
)

from .mark_handler import MarkHandler
from .pageview import PageView
from .pagescene import PageScene

# import the key-help popup window class
from .key_help import KeyHelp

from .useful_classes import (
    ErrorMessage,
    SimpleMessage,
    SimpleMessageCheckBox,
    NoAnswerBox,
)
from .comment_list import CommentWidget
from .origscanviewer import OriginalScansViewer
from .uiFiles.ui_annotator_rhm import Ui_annotator_rhm as Ui_annotator

log = logging.getLogger("annotr")

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


class Annotator(QWidget):
    """The main annotation window for annotating group-images
    and assigning marks.
    """

    ann_upload = pyqtSignal(str, list)
    ann_done_wants_more = pyqtSignal(str)
    ann_done_closing = pyqtSignal(str)
    ann_done_reject = pyqtSignal(str)

    def __init__(
        self,
        tgv,
        testname,
        paperdir,
        fnames,
        saveName,
        maxMark,
        markStyle,
        mouseHand,
        parent=None,
        plomDict=None,
    ):
        super(Annotator, self).__init__()
        # remember parent
        self.parent = parent
        # Grab filename of image, max mark, mark style (total/up/down)
        # and mouse-hand (left/right)
        self.tgv = tgv
        self.testname = testname
        self.paperdir = paperdir
        self.imageFiles = fnames
        self.saveName = saveName
        log.debug("Savename = {}".format(saveName))
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
        self.testViewFiles = None
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
        self.mouseHand = mouseHand
        self.ui = Ui_annotator()
        # Set up the gui.
        self.ui.setupUi(self)
        # hide the "revealbox" which is revealed when the hideBox is hidden.
        self.ui.revealBox0.setHidden(True)
        self.wideLayout()
        # Set up the graphicsview and graphicsscene of the group-image
        # loads in the image etc
        self.view = None
        self.scene = None
        self.setViewAndScene()

        # Create the comment list widget and put into gui.
        self.commentW = CommentWidget(self, self.maxMark)
        self.commentW.setTestname(testname)
        self.commentW.setQuestionNumberFromTGV(tgv)
        self.ui.commentGrid.addWidget(self.commentW, 1, 1)
        # pass the marking style to the mark entry widget.
        # also when we set this up we have to connect various
        # mark set, delta-set, mark change functions
        self.setMarkHandler(self.markStyle)
        self.setDeltaButtonMenu()
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
        # Grab window settings from parent
        self.loadWindowSettings()

        # Keyboard shortcuts.
        self.keycodes = self.getKeyCodes()

        # set up current-mark / current-mode label
        self.setCurrentMarkMode()

        # Connect various key-presses to associated tool-button clicks
        # Allows us to translate a key-press into a button-press.
        # Key layout (mostly) matches tool-button layout
        # Very last thing = unpickle scene from plomDict
        if plomDict is not None:
            self.unpickleIt(plomDict)
        self.timer = QElapsedTimer()
        self.timer.start()

        # TODO: use QAction, share with other UI, shortcut keys written once
        m = QMenu()
        m.addAction("Next paper\tctrl-n", self.saveAndGetNext)
        m.addAction("Done (save and close)", self.saveAndClose)
        m.addAction("Defer and go to next", self.menudummy).setEnabled(False)
        m.addSeparator()
        m.addAction("View whole paper", self.viewWholePaper)
        m.addSeparator()
        m.addAction("Compact UI\thome", self.narrowLayout)
        m.addAction("&Wide UI\thome", self.wideLayout)
        m.addSeparator()
        m.addAction("Help", self.menudummy).setEnabled(False)
        m.addAction("Show shortcut keys...\t?", self.keyPopUp)
        m.addAction("About Plom", self.menudummy).setEnabled(False)
        m.addSeparator()
        m.addAction("Close without saving\tctrl-c", self.close)
        self.ui.hamMenuButton.setMenu(m)
        self.ui.hamMenuButton.setToolTip("Menu (F10)")


    def menudummy(self):
        print("TODO: menu placeholder 1")

    def setCurrentMarkMode(self):
        self.ui.markLabel.setStyleSheet("color: #ff0000; font: bold;")
        self.ui.modeLabel.setText(" {} ".format(self.scene.mode))
        self.ui.markLabel.setText(
            "{} out of {}".format(self.scene.score, self.scene.maxMark)
        )

    def loadCursors(self):
        # https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
        # pyinstaller creates a temp folder and stores path in _MEIPASS

        try:
            base_path = sys._MEIPASS
        except Exception:
            # a hack - fix soon.
            base_path = os.path.join(os.path.dirname(__file__), "cursors")
            # base_path = "./cursors"

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
            Qt.Key_V: lambda: self.ui.commentDownButton.animateClick(),
            Qt.Key_B: lambda: self.ui.lineButton.animateClick(),
            # upper-row
            Qt.Key_Q: lambda: self.ui.panButton.animateClick(),
            Qt.Key_W: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_E: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_R: lambda: self.ui.commentUpButton.animateClick(),
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
            Qt.Key_M: lambda: self.ui.commentDownButton.animateClick(),
            Qt.Key_Comma: lambda: self.ui.boxButton.animateClick(),
            Qt.Key_Period: lambda: self.ui.deleteButton.animateClick(),
            Qt.Key_Slash: lambda: self.ui.moveButton.animateClick(),
            # top-row
            Qt.Key_Y: lambda: self.ui.penButton.animateClick(),
            Qt.Key_U: lambda: self.ui.commentUpButton.animateClick(),
            Qt.Key_I: lambda: self.ui.crossButton.animateClick(),
            Qt.Key_O: lambda: self.ui.redoButton.animateClick(),
            Qt.Key_P: lambda: self.ui.panButton.animateClick(),
            # Then maximize and mark buttons
            Qt.Key_Backslash: lambda: self.swapMaxNorm(),
            Qt.Key_Plus: lambda: self.view.zoomIn(),
            Qt.Key_Equal: lambda: self.view.zoomIn(),
            Qt.Key_Minus: lambda: self.view.zoomOut(),
            Qt.Key_Underscore: lambda: self.view.zoomOut(),
            # Change-mark shortcuts
            Qt.Key_QuoteLeft: lambda: self.keyToChangeMark(0),
            Qt.Key_1: lambda: self.keyToChangeMark(1),
            Qt.Key_2: lambda: self.keyToChangeMark(2),
            Qt.Key_3: lambda: self.keyToChangeMark(3),
            Qt.Key_4: lambda: self.keyToChangeMark(4),
            Qt.Key_5: lambda: self.keyToChangeMark(5),
            Qt.Key_6: lambda: self.keyToChangeMark(6),
            Qt.Key_7: lambda: self.keyToChangeMark(7),
            Qt.Key_8: lambda: self.keyToChangeMark(8),
            Qt.Key_9: lambda: self.keyToChangeMark(9),
            Qt.Key_0: lambda: self.keyToChangeMark(10),
            # ?-mark pop up a key-list
            Qt.Key_Question: lambda: self.keyPopUp(),
            # Toggle hide/unhide tools so as to maximise space for annotation
            Qt.Key_Home: lambda: self.toggleTools(),
            # view whole paper
            Qt.Key_F1: lambda: self.viewWholePaper(),
            Qt.Key_F10: lambda: self.ui.hamMenuButton.animateClick(),
        }

    def toggleTools(self):
        # Show / hide all the tools and so more space for the group-image
        # All tools in gui inside 'hideablebox' - so easily shown/hidden
        if self.ui.hideableBox.isHidden():
            self.wideLayout()
        else:
            self.narrowLayout()

    def narrowLayout(self):
        self.ui.revealBox0.show()
        self.ui.hideableBox.hide()
        self.ui.revealLayout.addWidget(self.ui.hamMenuButton, 0, 1, 1, 1)
        self.ui.revealLayout.addWidget(self.ui.finishedButton, 0, 2, 1, 1)
        ## TODO: just use an icon in compact?
        # self.ui.finishedButton.setText("N")
        # self.ui.finishedButton.setStyleSheet("padding-left: 1px; padding-right: 1px;")
        self.ui.finishedButton.setMaximumWidth(44)

        self.ui.revealLayout.addWidget(
            self.ui.zoomCB, 1, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.markLabel, 2, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.penButton, 4, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.lineButton, 4, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.tickButton, 5, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.crossButton, 5, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.textButton, 6, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.commentButton, 6, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.boxButton, 7, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.deltaButton, 7, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.deleteButton, 8, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.panButton, 8, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.undoButton, 8, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.redoButton, 8, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        self.ui.revealLayout.addWidget(
            self.ui.zoomButton, 9, 1, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.moveButton, 9, 2, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.modeLabel, 10, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )

    def wideLayout(self):
        self.ui.hideableBox.show()
        self.ui.revealBox0.hide()
        # right-hand mouse = 0, left-hand mouse = 1
        if self.mouseHand == 0:
            self.ui.horizontalLayout.addWidget(self.ui.hideableBox)
            self.ui.horizontalLayout.addWidget(self.ui.revealBox0)
            self.ui.horizontalLayout.addWidget(self.ui.pageFrame)
            # tools
            self.ui.toolLayout.addWidget(self.ui.panButton, 0, 0)
            self.ui.toolLayout.addWidget(self.ui.redoButton, 0, 1)
            self.ui.toolLayout.addWidget(self.ui.crossButton, 0, 2)
            self.ui.toolLayout.addWidget(self.ui.commentUpButton, 0, 3)
            self.ui.toolLayout.addWidget(self.ui.penButton, 0, 4)
            self.ui.toolLayout.addWidget(self.ui.zoomButton, 1, 0)
            self.ui.toolLayout.addWidget(self.ui.undoButton, 1, 1)
            self.ui.toolLayout.addWidget(self.ui.tickButton, 1, 2)
            self.ui.toolLayout.addWidget(self.ui.commentButton, 1, 3)
            self.ui.toolLayout.addWidget(self.ui.textButton, 1, 4)
            self.ui.toolLayout.addWidget(self.ui.moveButton, 2, 0)
            self.ui.toolLayout.addWidget(self.ui.deleteButton, 2, 1)
            self.ui.toolLayout.addWidget(self.ui.boxButton, 2, 2)
            self.ui.toolLayout.addWidget(self.ui.commentDownButton, 2, 3)
            self.ui.toolLayout.addWidget(self.ui.lineButton, 2, 4)
        else:  # left-hand mouse
            self.ui.horizontalLayout.addWidget(self.ui.pageFrame)
            self.ui.horizontalLayout.addWidget(self.ui.revealBox0)
            self.ui.horizontalLayout.addWidget(self.ui.hideableBox)
            # tools
            self.ui.toolLayout.addWidget(self.ui.penButton, 0, 0)
            self.ui.toolLayout.addWidget(self.ui.commentUpButton, 0, 1)
            self.ui.toolLayout.addWidget(self.ui.crossButton, 0, 2)
            self.ui.toolLayout.addWidget(self.ui.redoButton, 0, 3)
            self.ui.toolLayout.addWidget(self.ui.panButton, 0, 4)
            self.ui.toolLayout.addWidget(self.ui.textButton, 1, 0)
            self.ui.toolLayout.addWidget(self.ui.commentButton, 1, 1)
            self.ui.toolLayout.addWidget(self.ui.tickButton, 1, 2)
            self.ui.toolLayout.addWidget(self.ui.undoButton, 1, 3)
            self.ui.toolLayout.addWidget(self.ui.zoomButton, 1, 4)
            self.ui.toolLayout.addWidget(self.ui.lineButton, 2, 0)
            self.ui.toolLayout.addWidget(self.ui.commentDownButton, 2, 1)
            self.ui.toolLayout.addWidget(self.ui.boxButton, 2, 2)
            self.ui.toolLayout.addWidget(self.ui.deleteButton, 2, 3)
            self.ui.toolLayout.addWidget(self.ui.moveButton, 2, 4)
        self.ui.ebLayout.addWidget(self.ui.modeLabel)
        self.ui.modeLayout.addWidget(self.ui.hamMenuButton)
        self.ui.modeLayout.addWidget(self.ui.finishedButton)
        self.ui.finishedButton.setMaximumWidth(16777215)  # back to default
        self.ui.modeLayout.addWidget(self.ui.finishNoRelaunchButton)
        self.ui.buttonsLayout.addWidget(self.ui.markLabel)
        self.ui.buttonsLayout.addWidget(self.ui.zoomCB)

    def viewWholePaper(self):
        # grab the files if needed.
        if self.testViewFiles is None:
            testNumber = self.tgv[:4]
            log.debug("wholePage: downloading files for testnum {}".format(testNumber))
            pageNames, self.testViewFiles = self.parent.downloadWholePaper(testNumber)
            log.debug(
                "wholePage: pageNames = {}, viewFiles = {}".format(
                    pageNames, self.testViewFiles
                )
            )
        # if we haven't built a testview, built it now
        if self.testView is None:
            self.testView = OriginalScansViewer(self, testNumber, pageNames, self.testViewFiles)
        else:
            # must have closed it, so re-show it.
            self.testView.show()

    def doneViewingPaper(self):
        if self.testViewFiles:
            log.debug("wholePage: done with viewFiles {}".format(self.testViewFiles))
            # could just delete them here but maybe Marker wants to cache
            self.parent.doneWithWholePaperFiles(self.testViewFiles)
            self.testViewFiles = None
        if self.testView:
            self.testView.close()
            self.testView = None

    def keyPopUp(self):
        # build KeyPress shortcuts dialog
        kp = KeyHelp()
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
            self,
            self.imageFiles,
            self.saveName,
            self.maxMark,
            self.score,
            self.markStyle,
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
        """Translates a key-press (0,1,2,..,9) into a button-press
        of the various delta-mark buttons in the mark-entry widget.
        If mark-up style then they trigger the positive mark buttons,
        hence p0,p1 etc... if mark down then triggers the negative mark
        buttons - n1,n2, etc.
        """
        # if key is higher than maxMark then no such button.
        if buttonNumber > self.maxMark:
            return
        # Otherwise click the appropriate button.
        if self.markHandler.style == "Up":
            self.markHandler.markButtons["p{}".format(buttonNumber)].animateClick()
        elif self.markHandler.style == "Down" and buttonNumber >= 0:
            self.markHandler.markButtons["m{}".format(buttonNumber)].animateClick()

    def keyPressEvent(self, event):
        """Translates key-presses into tool-button presses if
        appropriate.
        """
        # Check to see if no mousebutton pressed
        # If a key-press detected use the keycodes dict to translate
        # the press into a function call (if exists)
        if QGuiApplication.mouseButtons() == Qt.NoButton:
            self.keycodes.get(event.key(), lambda *args: None)()
        super(Annotator, self).keyPressEvent(event)

    def setMode(self, newMode, newCursor):
        """Change the current tool mode.
        Changes the styling of the corresponding button, and
        also the cursor.
        """
        # self.currentButton should only ever be set to a button - nothing else.
        # Clear styling of the what was until now the current button
        if self.currentButton is not None:
            self.currentButton.setStyleSheet("")
        # A bit of a hack to take care of comment-mode and delta-mode
        if self.scene.mode == "comment" and newMode != "comment":
            # clear the comment button styling
            self.ui.commentButton.setStyleSheet("")
            self.commentW.CL.setStyleSheet("")
        if self.scene.mode == "delta" and newMode != "delta":
            self.ui.deltaButton.setStyleSheet("")
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
        elif isinstance(
            self.sender(), QToolButton
        ):  # only toolbuttons are the mode-changing ones.
            self.currentButton = self.sender()
            self.currentButton.setStyleSheet(self.currentButtonStyleBackground)
        elif self.sender() is self.commentW.CL:
            self.markHandler.clearButtonStyle()
            self.commentW.CL.setStyleSheet(self.currentButtonStyleOutline)
            self.ui.commentButton.setStyleSheet(self.currentButtonStyleBackground)
        elif self.sender() is self.markHandler:
            # Clear the style of the mark-handler (this will mostly not do
            # anything, but saves us testing if we had styled it)
            self.markHandler.clearButtonStyle()
            # this should not happen
        else:
            # this should also not happen - except by strange async race issues. So we don't change anything.
            pass
        # pass the new mode to the graphicsview, and set the cursor in view
        self.scene.setMode(newMode)
        self.view.setCursor(newCursor)
        # set the modelabel
        self.ui.modeLabel.setText(" {} ".format(self.scene.mode))
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
            # a hack - fix soon.
            base_path = os.path.join(os.path.dirname(__file__), "icons")
            # base_path = "./icons"

        self.setIcon(self.ui.boxButton, "box", "{}/rectangle_highlight.svg".format(base_path))
        self.setIcon(self.ui.commentButton, "com", "{}/comment.svg".format(base_path))
        self.setIcon(
            self.ui.commentDownButton, "com down", "{}/comment_down.svg".format(base_path)
        )
        self.setIcon(
            self.ui.commentUpButton, "com up", "{}/comment_up.svg".format(base_path)
        )
        self.setIcon(self.ui.crossButton, "cross", "{}/cross.svg".format(base_path))
        self.setIcon(self.ui.deleteButton, "delete", "{}/delete.svg".format(base_path))
        self.setIcon(self.ui.deltaButton, "delta", "{}/delta.svg".format(base_path))
        self.setIcon(self.ui.lineButton, "line", "{}/line.svg".format(base_path))
        self.setIcon(self.ui.moveButton, "move", "{}/move.svg".format(base_path))
        self.setIcon(self.ui.panButton, "pan", "{}/pan.svg".format(base_path))
        self.setIcon(self.ui.penButton, "pen", "{}/pen.svg".format(base_path))
        self.setIcon(self.ui.redoButton, "redo", "{}/redo.svg".format(base_path))
        self.setIcon(self.ui.textButton, "text", "{}/text.svg".format(base_path))
        self.setIcon(self.ui.tickButton, "tick", "{}/tick.svg".format(base_path))
        self.setIcon(self.ui.undoButton, "undo", "{}/undo.svg".format(base_path))
        self.setIcon(self.ui.zoomButton, "zoom", "{}/zoom.svg".format(base_path))

    @pyqtSlot()
    def saveAndGetNext(self):
        """Save the current annotations, and move on to the next paper.

        This saves the comment-list, closes the annotator. The marker
        window then asks the server for the next unmarked image and
        fires up a new annotator on that.
        """
        if self.saveAnnotations():
            self._priv_force_close = True
            self._priv_relaunch = True
            self.close()

    @pyqtSlot()
    def saveAndClose(self):
        """Save the current annotations, and then close."""
        if self.saveAnnotations():
            self._priv_force_close = True
            self._priv_relaunch = False
            self.close()

    def setMiscShortCuts(self):
        # shortcuts for next paper
        self.endShortCut = QShortcut(QKeySequence("Alt+Enter"), self)
        self.endShortCut.activated.connect(self.saveAndGetNext)
        self.endShortCutb = QShortcut(QKeySequence("Alt+Return"), self)
        self.endShortCutb.activated.connect(self.saveAndGetNext)
        self.endShortCutc = QShortcut(QKeySequence("Ctrl+n"), self)
        self.endShortCutc.activated.connect(self.saveAndGetNext)
        self.endShortCutd = QShortcut(QKeySequence("Ctrl+b"), self)
        self.endShortCutd.activated.connect(self.saveAndGetNext)
        self.cancelShortCut = QShortcut(QKeySequence("Ctrl+c"), self)
        self.cancelShortCut.activated.connect(self.close)
        # shortcuts for zoom-states
        self.zoomToggleShortCut = QShortcut(QKeySequence("Ctrl+="), self)
        self.zoomToggleShortCut.activated.connect(self.view.zoomToggle)
        # shortcuts for undo/redo
        self.undoShortCut = QShortcut(QKeySequence("Ctrl+z"), self)
        self.undoShortCut.activated.connect(self.scene.undo)
        self.redoShortCut = QShortcut(QKeySequence("Ctrl+y"), self)
        self.redoShortCut.activated.connect(self.scene.redo)
        # pan shortcuts
        self.panShortCut = QShortcut(QKeySequence("space"), self)
        self.panShortCut.activated.connect(self.view.panThrough)
        self.depanShortCut = QShortcut(QKeySequence("Shift+space"), self)
        self.depanShortCut.activated.connect(self.view.depanThrough)
        self.slowPanShortCut = QShortcut(QKeySequence("Ctrl+space"), self)
        self.slowPanShortCut.activated.connect(lambda: self.view.panThrough(0.02))
        self.slowDepanShortCut = QShortcut(QKeySequence("Ctrl+Shift+space"), self)
        self.slowDepanShortCut.activated.connect(lambda: self.view.depanThrough(0.02))

    # Simple mode change functions
    def boxMode(self):
        self.setMode("box", self.cursorBox)

    def commentMode(self):
        if self.scene.mode == "comment":
            self.commentW.nextItem()
        else:
            self.commentW.currentItem()
        self.commentW.CL.handleClick()

    def crossMode(self):
        self.setMode("cross", self.cursorCross)

    def deleteMode(self):
        self.setMode("delete", self.cursorDelete)

    def deltaButtonMode(self):
        if QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier:
            self.ui.deltaButton.showMenu()
        else:
            self.setMode("delta", Qt.IBeamCursor)

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
        # Also the "hidden" delta-button
        self.ui.deltaButton.clicked.connect(self.deltaButtonMode)

        # Pass the undo/redo button clicks on to the view
        self.ui.undoButton.clicked.connect(self.scene.undo)
        self.ui.redoButton.clicked.connect(self.scene.redo)
        # The key-help button connects to the keyPopUp command.
        # TODO: messy viz hacks
        # self.ui.keyHelpButton.clicked.connect(self.keyPopUp)
        self.ui.keyHelpButton.setVisible(False)
        self.ui.cancelButton.setVisible(False)
        # The view button connects to the viewWholePaper
        # self.ui.viewButton.clicked.connect(self.viewWholePaper)
        self.ui.viewButton.setVisible(False)

        # Cancel button closes annotator(QDialog) with a 'reject' via the cleanUpCancel function
        self.ui.cancelButton.clicked.connect(self.close)

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
        self.ui.finishedButton.clicked.connect(self.saveAndGetNext)
        self.ui.finishNoRelaunchButton.clicked.connect(self.saveAndClose)
        # Connect the "no answer" button
        self.ui.noAnswerButton.clicked.connect(self.noAnswer)

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
        # Else, the delta is now set, so now change the mode here.
        self.setMode("delta", QCursor(Qt.IBeamCursor))
        # and set style of the delta-button
        self.ui.deltaButton.setStyleSheet(self.currentButtonStyleBackground)

    def changeMark(self, score):
        """The mark has been changed. Update the mark-handler.
        """
        # Tell the mark-handler what the new mark is and force a repaint.
        assert self.markStyle != 1, "Should not be called if mark-total"

        self.score = score
        # update the markline
        self.ui.markLabel.setText(
            "{} out of {}".format(self.scene.score, self.scene.maxMark)
        )
        self.markHandler.setMark(self.score)
        self.markHandler.repaint()
        # update the delta-mark-menu
        self.updateDeltaMarkMenu()

    def loadWindowSettings(self):
        # load the window geometry, else maximise.
        if self.parent.annotatorSettings["geometry"] is not None:
            self.restoreGeometry(self.parent.annotatorSettings["geometry"])
            # TODO - delete the below
            # since we can't directly jsonify QByteArray:
            # self.restoreGeometry(
            #     QByteArray.fromBase64(
            #         self.parent.annotatorSettings["geometry"].encode()
            #     )
            # )
        else:
            # Make sure window is maximised.
            self.showMaximized()

        # remember the "do not show again" checks
        if self.parent.annotatorSettings["markWarnings"] is not None:
            self.markWarn = self.parent.annotatorSettings["markWarnings"]
        if self.parent.annotatorSettings["commentWarnings"] is not None:
            self.commentWarn = self.parent.annotatorSettings["commentWarnings"]

        # remember the last tool used
        if self.parent.annotatorSettings["tool"] is not None:
            if self.parent.annotatorSettings["tool"] == "delta":
                dlt = self.parent.annotatorSettings["delta"]
                self.loadModeFromBefore("delta", dlt)
            elif self.parent.annotatorSettings["tool"] == "comment":
                cmt = self.parent.annotatorSettings["comment"]
                self.loadModeFromBefore("comment", cmt)
            else:
                self.loadModeFromBefore(self.parent.annotatorSettings["tool"])

        # if zoom-state is none, set it to index 1 (fit page) - but delay.
        if self.parent.annotatorSettings["zoomState"] is None:
            QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(1))
        elif self.parent.annotatorSettings["zoomState"] == 0:
            # is set to "user", so set the view-rectangle
            if self.parent.annotatorSettings["viewRectangle"] is not None:
                QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(0))
                QTimer.singleShot(
                    200,
                    lambda: self.view.initialZoom(
                        self.parent.annotatorSettings["viewRectangle"]
                    ),
                )
            else:
                # no view-rectangle, so set to "fit-page"
                QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(1))
        else:
            QTimer.singleShot(
                200,
                lambda: self.ui.zoomCB.setCurrentIndex(
                    self.parent.annotatorSettings["zoomState"]
                ),
            )
        # wide vs compact
        if self.parent.annotatorSettings["compact"] is True:
            log.debug("compacting UI (b/c of last use setting")
            self.toggleTools()

    def saveWindowSettings(self):
        # TODO - delete below
        # since we can't directly jsonify QByteArray:
        # self.parent.annotatorSettings["geometry"] = (
        #     self.saveGeometry().toBase64().data().decode()
        # )
        # since we can't directly jsonify qrectf:
        # jsrect = self.view.getCurrentViewRect()
        # self.parent.annotatorSettings["viewRectangle"] = [
        #     jsrect.x(),
        #     jsrect.y(),
        #     jsrect.width(),
        #     jsrect.height(),
        # ]
        self.parent.annotatorSettings["geometry"] = self.saveGeometry()
        self.parent.annotatorSettings["viewRectangle"] = self.view.getCurrentViewRect()
        self.parent.annotatorSettings["markWarnings"] = self.markWarn
        self.parent.annotatorSettings["commentWarnings"] = self.commentWarn
        self.parent.annotatorSettings["zoomState"] = self.ui.zoomCB.currentIndex()
        self.parent.annotatorSettings["tool"] = self.scene.mode
        if self.scene.mode == "delta":
            self.parent.annotatorSettings["delta"] = self.scene.markDelta
        if self.scene.mode == "comment":
            self.parent.annotatorSettings["comment"] = self.commentW.getCurrentItemRow()

        if self.ui.hideableBox.isVisible():
            self.parent.annotatorSettings["compact"] = False
        else:
            self.parent.annotatorSettings["compact"] = True

    def saveAnnotations(self):
        """Try to save the annotations and signal Marker to upload them.

        There are various sanity checks and user interaction to be
        done.  Return `False` if user cancels.  Return `True` if we
        should move on (for example, to close the Annotator).

        Be careful of a score of 0 - when mark total or mark up.
        Be careful of max-score when marking down.
        In either case - get user to confirm the score before closing.
        Also confirm various "not enough feedback" cases.
        """
        # do some checks before accepting things
        if not self.scene.areThereAnnotations():
            msg = ErrorMessage("Please make an annotation, even if there is no answer.")
            msg.exec_()
            return False

        # warn if points where lost but insufficient annotations
        if (
            self.commentWarn
            and self.score > 0
            and self.score < self.maxMark
            and self.scene.hasOnlyTicksCrossesDeltas()
        ):
            msg = SimpleMessageCheckBox(
                "<p>You have given neither comments nor detailed annotations "
                "(other than &#x2713; &#x2717; &plusmn;<i>n</i>).</p>\n"
                "<p>This may make it difficult for students to learn from this "
                "feedback.</p>\n"
                "<p>Are you sure you wish to continue?</p>",
                "Don't ask me again this session.",
            )
            if msg.exec_() == QMessageBox.No:
                return False
            if msg.cb.checkState() == Qt.Checked:
                # Note: these are only saved if we ultimately accept
                self.commentWarn = False

        # if marking total or up, be careful when giving 0-marks
        if self.score == 0 and self.markHandler.style != "Down":
            warn = False
            forceWarn = False
            msg = "<p>You have given <b>0/{}</b>,".format(self.maxMark)
            if self.scene.hasOnlyTicks():
                warn = True
                forceWarn = True
                msg += " but there are <em>only ticks on the page!</em>"
            elif self.scene.hasAnyTicks():
                # forceWarn = True
                warn = True
                msg += " but there are some ticks on the page."
            if warn:
                msg += "  Please confirm, or consider using comments to clarify.</p>"
                msg += "\n<p>Do you wish to submit?</p>"
                if forceWarn:
                    msg = SimpleMessage(msg)
                    if msg.exec_() == QMessageBox.No:
                        return False
                elif self.markWarn:
                    msg = SimpleMessageCheckBox(msg, "Don't ask me again this session.")
                    if msg.exec_() == QMessageBox.No:
                        return False
                    if msg.cb.checkState() == Qt.Checked:
                        self.markWarn = False

        # if marking down, be careful of giving max-marks
        if self.score == self.maxMark and self.markHandler.style == "Down":
            msg = "<p>You have given full {0}/{0},".format(self.maxMark)
            forceWarn = False
            if self.scene.hasOnlyTicks():
                warn = False
            elif self.scene.hasOnlyCrosses():
                warn = True
                forceWarn = True
                msg += " <em>but there are only crosses on the page!</em>"
            elif self.scene.hasAnyCrosses():
                warn = True
                # forceWarn = True
                msg += " but there are crosses on the page."
            elif self.scene.hasAnyComments():
                warn = False
            else:
                warn = True
                msg += " but there are other annotations on the page which might be contradictory."
            if warn:
                msg += "  Please confirm, or consider using comments to clarify.</p>"
                msg += "\n<p>Do you wish to submit?</p>"
                if forceWarn:
                    msg = SimpleMessage(msg)
                    if msg.exec_() == QMessageBox.No:
                        return False
                elif self.markWarn:
                    msg = SimpleMessageCheckBox(msg, "Don't ask me again this session.")
                    if msg.exec_() == QMessageBox.No:
                        return False
                    if msg.cb.checkState() == Qt.Checked:
                        self.markWarn = False

        if not self.scene.checkAllObjectsInside():
            msg = SimpleMessage(
                "Some annotations are outside the page image. "
                "Do you really want to finish?"
            )
            if msg.exec_() == QMessageBox.No:
                return False

        # clean up after a testview
        self.doneViewingPaper()

        # Save the scene to file.
        self.scene.save()
        # Save the marker's comments
        self.saveMarkerComments()
        # Pickle the scene as a plom-file
        self.pickleIt()

        # Save the current window settings for next time annotator is launched
        self.saveWindowSettings()
        self.commentW.saveComments()

        log.debug("emitting accept signal")
        tim = self.timer.elapsed() // 1000
        # some things here hardcoded elsewhere too, and up in marker
        plomFile = self.saveName[:-3] + "plom"
        commentFile = self.saveName[:-3] + "json"
        stuff = [
            self.score,
            tim,
            self.paperdir,
            self.imageFiles,
            self.saveName,
            plomFile,
            commentFile,
        ]
        self.ann_upload.emit(self.tgv, stuff)
        return True

    def closeEvent(self, ce):
        """Deal with various cases of window trying to close.

        There are various things that can happen.
          * User closes window via titlebar close icon (or alt-f4 or...)
          * User clicks "Cancel"
          * User clicks "Next"
          * User clicks "Done"

        Currently all these events end up here, eventually.

        Window close or Cancel are currently treated the same way:
        discard all annotations.
        """
        # weird hacking to force close if we came from saving.
        # Appropriate signals have already been sent so just close
        force = getattr(self, "_priv_force_close", False)
        if force:
            if self._priv_relaunch:
                log.debug("emitting the WantsMore signal")
                self.ann_done_wants_more.emit(self.tgv)
            else:
                log.debug("emitting the closing signal")
                self.ann_done_closing.emit(self.tgv)
            ce.accept()
            return

        # We are here b/c of cancel button, titlebar close, or related
        if self.scene.areThereAnnotations():
            msg = SimpleMessage(
                "<p>There are annotations on the page.</p>\n"
                "<p>Do you want to discard them and close the annotator?</p>"
            )
            if msg.exec_() == QMessageBox.No:
                ce.ignore()
                return
        log.debug("emitting reject/cancel signal, discarding, and closing")
        self.ann_done_reject.emit(self.tgv)
        # clean up after a testview
        self.doneViewingPaper()
        ce.accept()

    def getComments(self):
        return self.scene.getComments()

    def saveMarkerComments(self):
        commentList = self.getComments()
        # savefile is <blah>.png, save comments as <blah>.json
        with open(self.saveName[:-3] + "json", "w") as commentFile:
            json.dump(commentList, commentFile)

    def latexAFragment(self, txt):
        return self.parent.latexAFragment(txt)

    def pickleIt(self):
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        plomDict = {
            "fileNames": [os.path.basename(fn) for fn in self.imageFiles],
            "saveName": os.path.basename(self.saveName),
            "markStyle": self.markStyle,
            "maxMark": self.maxMark,
            "currentMark": self.score,
            "sceneItems": lst,
        }
        # save pickled file as <blah>.plom
        plomFile = self.saveName[:-3] + "plom"
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
        self.ui.zoomCB.addItem("Fit page")
        self.ui.zoomCB.addItem("Fit width")
        self.ui.zoomCB.addItem("Fit height")
        self.ui.zoomCB.addItem("200%")
        self.ui.zoomCB.addItem("150%")
        self.ui.zoomCB.addItem("100%")
        self.ui.zoomCB.addItem("50%")
        self.ui.zoomCB.addItem("33%")
        self.ui.zoomCB.currentIndexChanged.connect(self.zoomCBChanged)

    def isZoomFitWidth(self):
        return self.ui.zoomCB.currentText() == "Fit width"

    def isZoomFitHeight(self):
        return self.ui.zoomCB.currentText() == "Fit height"

    def changeCBZoom(self, v):
        old = self.ui.zoomCB.blockSignals(True)
        self.ui.zoomCB.setCurrentIndex(v)
        self.ui.zoomCB.blockSignals(old)

    def zoomCBChanged(self):
        if self.ui.zoomCB.currentText() == "Fit page":
            self.view.zoomAll()
        elif self.ui.zoomCB.currentText() == "Fit width":
            self.view.zoomWidth()
        elif self.ui.zoomCB.currentText() == "Fit height":
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

    def setDeltaButtonMenu(self):
        if self.markStyle == 1:
            # mark total - don't set anything
            return
        self.ui.deltaMenu = QMenu("Set Delta")
        self.deltaActions = {}
        if self.markStyle == 2:
            # set to mark up
            for k in range(0, self.maxMark + 1):
                self.deltaActions[k] = self.ui.deltaMenu.addAction("+{}".format(k))
                self.deltaActions[k].triggered.connect(
                    self.markHandler.markButtons["p{}".format(k)].animateClick
                )
        elif self.markStyle == 3:
            # set to mark down
            for k in range(0, self.maxMark + 1):
                self.deltaActions[k] = self.ui.deltaMenu.addAction("-{}".format(k))
                self.deltaActions[k].triggered.connect(
                    self.markHandler.markButtons["m{}".format(k)].animateClick
                )
        self.ui.deltaButton.setMenu(self.ui.deltaMenu)
        self.updateDeltaMarkMenu()

    def updateDeltaMarkMenu(self):
        if self.markStyle == 1:
            return
        elif self.markStyle == 2:
            for k in range(0, self.maxMark + 1):
                if self.score + k <= self.maxMark:
                    self.deltaActions[k].setEnabled(True)
                else:
                    self.deltaActions[k].setEnabled(False)
        elif self.markStyle == 3:
            for k in range(0, self.maxMark + 1):
                if self.score >= k:
                    self.deltaActions[k].setEnabled(True)
                else:
                    self.deltaActions[k].setEnabled(False)

    def noAnswer(self):
        if self.markStyle == 2:
            if self.score > 0:  # is mark-up
                ErrorMessage(
                    'You have added marks - cannot then set "No answer given". Delete deltas before trying again.'
                ).exec_()
                return
            else:
                self.scene.noAnswer(0)
        elif self.markStyle == 3:
            if self.score < self.maxMark:  # is mark-down
                ErrorMessage(
                    'You have deducted marks - cannot then set "No answer given". Delete deltas before trying again.'
                ).exec()
                return
            else:
                self.scene.noAnswer(-self.maxMark)
        nabValue = NoAnswerBox().exec_()
        if nabValue == 0:
            # equivalent to cancel - apply undo three times (to remove the noanswer lines+comment)
            self.scene.undo()
            self.scene.undo()
            self.scene.undo()
        elif nabValue == 1:
            # equivalent to "yes - give me next paper"
            self.ui.finishedButton.animateClick()
        else:
            pass
