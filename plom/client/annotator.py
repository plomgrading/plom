# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Elvis Cai", "Colin Macdonald", "Victoria Schuster"]
__license__ = "AGPLv3"

import json
import logging
import os
import re
import sys
import tempfile
from textwrap import dedent

from PyQt5.QtCore import (
    Qt,
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
)
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QShortcut,
    QToolButton,
    QFileDialog,
    QColorDialog,
)

from .comment_list import CommentWidget

# import the key-help popup window class
from .key_help import KeyHelp
from .mark_handler import MarkHandler
from .origscanviewer import OriginalScansViewer, RearrangementViewer
from .pagescene import PageScene
from .pageview import PageView
from .uiFiles.ui_annotator_rhm import Ui_annotator_rhm as Ui_annotator
from .useful_classes import (
    ErrorMessage,
    SimpleMessage,
    SimpleMessageCheckBox,
    NoAnswerBox,
)


log = logging.getLogger("annotr")

# Short descriptions of each tool to display to user.
tipText = {
    "box": "Box: L = highlighted box, R/Shift = highlighted ellipse.",
    "com": "Comment: L = paste comment and associated mark, R/Shift = labelled box",
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
    """The main annotation window for annotating group-images.

    A subclass of QWidget
    """

    annotator_upload = pyqtSignal(str, list)
    annotator_done_closing = pyqtSignal(str)
    annotator_done_reject = pyqtSignal(str)

    def __init__(self, username, mouseHand, parentMarkerUI=None, initialData=None):
        """
        Initializes a new annotator window.

        Args:
            username (str): username of Marker
            mouseHand (int): The location of the grader's mouse hand. (
                Right = 0, Left != 0)
            parentMarkerUI (MarkerClient): the parent of annotator UI.
            initialData (dict): as documented by the arguments to "loadNewTGV"
        """
        super().__init__()

        self.username = username
        self.parentMarkerUI = parentMarkerUI
        self.tgvID = None

        # Show warnings or not
        self.markWarn = True
        self.commentWarn = True

        # a test view pop-up window - initially set to None for viewing whole paper
        self.testView = None
        self.testViewFiles = None

        # declares some instance vars
        self.cursorBox = None
        self.cursorCross = None
        self.cursorDelete = None
        self.cursorEllipse = None
        self.cursorLine = None
        self.cursorPen = None
        self.cursorTick = None
        self.cursorQMark = None
        self.cursorArrow = None
        self.cursorHighlight = None
        self.cursorDoubleArrow = None
        self.testName = None
        self.paperDir = None
        self.src_img_data = None
        self.saveName = None
        self.score = None
        self.maxMark = None

        # when comments are used, we just outline the comment list - not
        # the whole background - so make a style for that.
        self.currentButtonStyleOutline = "border: 2px solid #3daee9; "

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
        self.view = PageView(self, self.username)
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)

        # Create the comment list widget and put into gui.
        self.comment_widget = CommentWidget(self, None)
        self.ui.container_commentwidget.addWidget(self.comment_widget)

        # pass the marking style to the mark entry widget.
        # also when we set this up we have to connect various
        # mark set, delta-set, mark change functions
        self.scene = None  # TODO?
        self.markHandler = None

        self.setMiscShortCuts()
        # set the zoom combobox
        self.setZoomComboBox()
        # Set the tool icons
        self.setAllIcons()
        # Set up cursors
        self.loadCursors()

        # Connect all the buttons to relevant functions
        self.setButtons()
        # Make sure window has min/max buttons.
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint
        )

        # Keyboard shortcuts.
        self.key_codes = self.getKeyShortcuts()

        self.timer = QElapsedTimer()

        self.modeInformation = ["move"]

        if initialData:
            self.loadNewTGV(*initialData)

        # Grab window settings from parent
        self.loadWindowSettings()

        # TODO: use QAction, share with other UI, shortcut keys written once
        m = QMenu()
        m.addAction("Next paper\tctrl-n", self.saveAndGetNext)
        m.addAction("Done (save and close)", self.saveAndClose)
        m.addAction("Defer and go to next", lambda: None).setEnabled(False)
        m.addSeparator()
        m.addAction("Insert image", self.addImageMode)
        m.addSeparator()
        m.addAction("View whole paper", self.viewWholePaper)
        m.addAction("Adjust pages\tCtrl-r", self.rearrangePages)
        m.addSeparator()
        m.addAction("Compact UI\thome", self.narrowLayout)
        m.addAction("&Wide UI\thome", self.wideLayout)
        m.addSeparator()
        m.addAction(
            "Increase annotation scale\tshift-]", lambda: self.change_annot_scale(1.1)
        )
        # Keep a reference to this one so we can update the text
        self._reset_scale_menu_text = "Reset annotation scale"
        self._reset_scale_QAction = m.addAction(
            self._reset_scale_menu_text, self.change_annot_scale
        )
        self.update_annot_scale_menu_label()

        m.addAction(
            "Decrease annotation scale\tshift-]",
            lambda: self.change_annot_scale(1.0 / 1.1),
        )
        # Issue #1350: temporarily?
        m.addAction(
            "Temporarily change annot. colour",
            self.change_annotation_colour,
        )
        m.addSeparator()
        m.addAction("Help", lambda: None).setEnabled(False)
        m.addAction("Show shortcut keys...\t?", self.keyPopUp)
        m.addAction("About Plom", lambda: None).setEnabled(False)
        m.addSeparator()
        m.addAction("Close without saving\tctrl-c", self.close)
        self.ui.hamMenuButton.setMenu(m)
        self.ui.hamMenuButton.setToolTip("Menu (F10)")
        self.ui.hamMenuButton.setPopupMode(QToolButton.InstantPopup)

    def closeCurrentTGV(self):
        """
        Closes the current Test Group Version (closes scene tgv and sets relevant files to None)

        Notes:
            As a result of this method, there are occasions where many instance variables will be None.
            Be cautious of how these variables will be handled in cases where they are None.

        Returns:
            None: Modifies self

        """

        # TODO: self.view.disconnectFrom(self.scene)
        # self.view = None
        # TODO: how to reset the scene?
        # This may be heavy handed, but for now we delete the old scene

        # Attempt at keeping mode information.
        self.modeInformation = [self.scene.mode]
        if self.scene.mode == "delta":
            self.modeInformation.append(self.scene.markDelta)
        elif self.scene.mode == "comment":
            self.modeInformation.append(self.comment_widget.getCurrentItemRow())

        # after grabbed mode information, reset comment_widget
        self.comment_widget.reset()

        del self.scene
        self.scene = None

        # clean up after a testview
        self.doneViewingPaper()
        self.testView = None
        self.testViewFiles = None
        self.tgvID = None
        self.testName = None
        self.setWindowTitle("Annotator")
        self.paperDir = None
        self.src_img_data = None
        self.saveName = None
        # self.destroyMarkHandler()

    def loadNewTGV(
        self,
        tgvID,
        testName,
        paperdir,
        saveName,
        maxMark,
        markStyle,
        plomDict,
        integrity_check,
        src_img_data,
    ):
        """Loads new Data into the Toggle View window for marking.

        TODO: maintain current tool not working yet: #799.

        Args:
            tgvID (str):  Test-Group-Version ID.
                            For Example: for Test # 0027, group # 13, Version #2
                                         tgv = t0027g13v2
            testName (str): Test Name
            paperdir (dir): Working directory for the current task
            saveName (str): name the tgv is saved as
            maxMark (int): maximum possible score for that test question
            markStyle (int): marking style
                             1 = mark total = user clicks the total-mark
                             2 = mark-up = mark starts at 0 and user increments it
                             3 = mark-down = mark starts at max and user decrements it
                             Note: can be overridden by the plomDict.
            plomDict (dict) : a dictionary of annotation information.
                                A dict that contains sufficient information to recreate the
                                annotation objects on the page if you go back to continue annotating a
                                question. ie - is it mark up/down, where are all the objects, how to
                                rebuild those objects, etc.
            integrity_check (str): integrity check string
            src_img_data (list[dict]): image md5sums, filenames etc.

        Returns:
            None: Modifies many instance vars.

        """
        self.tgvID = tgvID
        self.question_num = int(re.split(r"\D+", tgvID)[-1])
        self.testName = testName
        s = "Q{} of {}: {}".format(self.question_num, testName, tgvID)
        self.setWindowTitle("{} - Plom Annotator".format(s))
        log.info("Annotating {}".format(s))
        self.paperDir = paperdir
        self.saveName = saveName
        self.integrity_check = integrity_check
        self.src_img_data = src_img_data

        if getattr(self, "maxMark", None) != maxMark:
            log.warning("Is changing maxMark supported?  we just did it...")
        self.maxMark = maxMark
        del maxMark

        log.debug("Plom data (truncated):\n{}".format(str(plomDict)[:255]))
        if plomDict:
            self.markStyle = plomDict["markStyle"]
        else:
            self.markStyle = markStyle
        del markStyle  # prevent use of non-overridden value
        log.debug("markstyle = {}".format(self.markStyle))

        if plomDict:
            assert plomDict["maxMark"] == self.maxMark, "mismatch between maxMarks"

        # Set current mark to 0.
        # 2 = mark-up = mark starts at 0 and user increments it
        # 3 = mark-down = mark starts at max and user decrements it
        if self.markStyle == 2:  # markUp
            self.score = 0
        elif self.markStyle == 3:  # markDown
            self.score = self.maxMark
        else:  # must be mark-total
            log.warning("Using mark-total. This should not happen.")
            self.score = 0

        # Set up the graphicsview and graphicsscene of the group-image
        # loads in the image etc
        self.view.setHidden(False)  # or try not hiding it...
        self.setViewAndScene()
        # TODO: see above, can we maintain our zoom b/w images?  Would anyone want that?
        # TODO: see above, don't click a different button: want to keep same tool

        # TODO: perhaps not right depending on when `self.setMarkHandler(self.markStyle)` is called
        self.comment_widget.setStyle(self.markStyle)
        self.comment_widget.maxMark = (
            self.maxMark  # TODO: add helper?  combine with changeMark?
        )
        self.comment_widget.changeMark(self.score)
        self.comment_widget.setQuestionNumber(self.question_num)
        self.comment_widget.setTestname(testName)

        if not self.markHandler:
            # Build the mark handler and put into the gui.
            self.markHandler = MarkHandler(self, self.maxMark, self.markStyle)
            self.ui.container_markgrid.addWidget(self.markHandler)
        else:
            self.markHandler.resetAndMaybeChange(self.maxMark, self.markStyle)

        # update the displayed score - fixes #843
        self.changeMark(self.score)

        # Very last thing = unpickle scene from plomDict
        if plomDict is not None:
            self.unpickleIt(plomDict)

        # TODO: Make handling of comment less hack.
        log.debug("Restore mode info = {}".format(self.modeInformation))
        self.scene.setToolMode(self.modeInformation[0])
        if self.modeInformation[0] == "delta":
            self.markHandler.clickDelta(self.modeInformation[1])
        if self.modeInformation[0] == "comment":
            self.comment_widget.setCurrentItemRow(self.modeInformation[1])
            self.comment_widget.CL.handleClick()

        # reset the timer (its not needed to make a new one)
        self.timer.start()

    def change_annot_scale(self, scale=None):
        """Change the scale of the annotations.

        args:
            scale (float/None): if None reset the scale to the default.
                If any floating point number, multiple the scale by that
                value.
        """
        if scale is None:
            log.info("resetting annotation scale to default")
            if self.scene:
                self.scene.reset_scale_factor()
            self.update_annot_scale_menu_label()

            return
        log.info("multiplying annotation scale by {}".format(scale))
        if self.scene:
            self.scene.increase_scale_factor(scale)
        self.update_annot_scale_menu_label()

    def update_annot_scale_menu_label(self):
        """Update the menu which shows the current annotation scale."""
        if not self.scene:
            return
        self._reset_scale_QAction.setText(
            self._reset_scale_menu_text
            + "\t{:.0%}".format(self.scene.get_scale_factor())
        )

    def change_annotation_colour(self):
        """Ask user for a new colour for the annotations."""
        if not self.scene:
            return
        c = self.scene.ink.color()
        c = QColorDialog.getColor(c)
        if c.isValid():
            self.scene.set_annotation_color(c)
        # TODO: save to settings

    def setCurrentMarkMode(self):
        """
        TODO: check this.
        Checks if page scene (self.scene) is not none, in which case

        Returns:
            None

        """
        self.ui.markLabel.setStyleSheet("color: #ff0000; font: bold;")
        if self.scene:
            self.ui.modeLabel.setText(" {} ".format(self.scene.mode))
        self.ui.markLabel.setText("{} out of {}".format(self.score, self.maxMark))

    def loadCursors(self):
        """
        Loads Cursors by generating a temp folder in _MEIPASS to store cursors.

        Starts by:
            1. Reads the path to PyInstaller's temporary folder through sys._MEIPASS
               More info at: https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
            2. uses QCursor to using step 1's path to set the cursor path,

        Returns:
            None
        """

        try:
            base_path = sys._MEIPASS
        except Exception:
            # a hack - fix soon.
            base_path = os.path.join(os.path.dirname(__file__), "cursors")
            # base_path = "./cursors"

        # load pixmaps for cursors and set the hotspots
        self.cursorBox = QCursor(QPixmap("{}/box.png".format(base_path)), 4, 4)
        self.cursorEllipse = QCursor(QPixmap("{}/ellipse.png".format(base_path)), 4, 4)
        self.cursorCross = QCursor(QPixmap("{}/cross.png".format(base_path)), 4, 4)
        self.cursorDelete = QCursor(QPixmap("{}/delete.png".format(base_path)), 4, 4)
        self.cursorLine = QCursor(QPixmap("{}/line.png".format(base_path)), 4, 4)
        self.cursorPen = QCursor(QPixmap("{}/pen.png".format(base_path)), 4, 4)
        self.cursorTick = QCursor(QPixmap("{}/tick.png".format(base_path)), 4, 4)
        self.cursorQMark = QCursor(
            QPixmap("{}/question_mark.png".format(base_path)), 4, 4
        )
        self.cursorHighlight = QCursor(
            QPixmap("{}/highlighter.png".format(base_path)), 4, 4
        )
        self.cursorArrow = QCursor(QPixmap("{}/arrow.png".format(base_path)), 4, 4)
        self.cursorDoubleArrow = QCursor(
            QPixmap("{}/double_arrow.png".format(base_path)), 4, 4
        )

    def getKeyShortcuts(self):
        """
        Builds dictionary containing hotkeys and their actions.

        Returns:
            (Dict): a dictionary containing hot keys for annotator.
        """
        if self.mouseHand == 0:
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
        else:
            return {
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
        """
        Shows/Hides tools making more space to view the group-image.

        Returns:
            None: modifies self.ui.hideableBox
        """
        # All tools in gui inside 'hideablebox' - so easily shown/hidden
        if self.ui.hideableBox.isHidden():
            self.wideLayout()
        else:
            self.narrowLayout()

    def narrowLayout(self):
        """
        Changes view to narrow Layout style.

        Returns:
            None: modifies self.ui

        """
        self.ui.revealBox0.show()
        self.ui.hideableBox.hide()
        self.ui.revealLayout.addWidget(self.ui.hamMenuButton, 0, 1, 1, 1)
        self.ui.revealLayout.addWidget(self.ui.finishedButton, 0, 2, 1, 1)
        # TODO: just use an icon in compact?
        # self.ui.finishedButton.setText("N")
        # self.ui.finishedButton.setStyleSheet("padding-left: 1px; padding-right: 1px;")
        self.ui.finishedButton.setMaximumWidth(44)

        to_reveal = [
            [self.ui.penButton, 4, 1],
            [self.ui.lineButton, 4, 2],
            [self.ui.tickButton, 5, 1],
            [self.ui.crossButton, 5, 2],
            [self.ui.textButton, 6, 1],
            [self.ui.commentButton, 6, 2],
            [self.ui.boxButton, 7, 1],
            [self.ui.deltaButton, 7, 2],
            [self.ui.deleteButton, 8, 1],
            [self.ui.panButton, 8, 2],
            [self.ui.undoButton, 8, 1],
            [self.ui.redoButton, 8, 2],
            [self.ui.zoomButton, 9, 1],
            [self.ui.moveButton, 9, 2],
        ]

        self.ui.revealLayout.addWidget(
            self.ui.zoomCB, 1, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )
        self.ui.revealLayout.addWidget(
            self.ui.markLabel, 2, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )

        for button in to_reveal:
            self.ui.revealLayout.addWidget(
                button[0], button[1], button[2], Qt.AlignHCenter | Qt.AlignTop
            )

        self.ui.deltaButton.setVisible(True)

        self.ui.revealLayout.addWidget(
            self.ui.modeLabel, 10, 1, 1, 2, Qt.AlignHCenter | Qt.AlignTop
        )

    def wideLayout(self):
        """
        Changes view to Wide Layout style.

        Returns:
            None: modifies self.ui
        """
        self.ui.hideableBox.show()
        self.ui.revealBox0.hide()

        def load_tools(mouse_hand):
            """
            Loads tools based on left or right handed mouse.

            Args:
                mouse_hand(int): left or right handed mouse. Right = 0, Left != 0

            Returns:
                None: adds tool widgets to self.ui.toolLayout
            """
            tools = [
                [
                    self.ui.panButton,
                    self.ui.redoButton,
                    self.ui.crossButton,
                    self.ui.commentUpButton,
                    self.ui.penButton,
                ],
                [
                    self.ui.zoomButton,
                    self.ui.undoButton,
                    self.ui.tickButton,
                    self.ui.commentButton,
                    self.ui.textButton,
                ],
                [
                    self.ui.moveButton,
                    self.ui.deleteButton,
                    self.ui.boxButton,
                    self.ui.commentDownButton,
                    self.ui.lineButton,
                    self.ui.deltaButton,
                ],
            ]

            row_index = 0
            for row in tools:
                column_index = 0
                # right handed mouse
                if mouse_hand == 0:
                    for tool in row:
                        self.ui.toolLayout.addWidget(tool, row_index, column_index)
                        column_index += 1
                else:
                    # if left handed, loads column elements in reverse order (right to left)
                    for tool in reversed(row):
                        self.ui.toolLayout.addWidget(tool, row_index, column_index)
                        column_index += 1
                row_index += 1

        # TODO: not polite to be grubbing around in parent.ui, fix with QSetting
        if self.parentMarkerUI.ui.sidebarRightCB.isChecked():
            self.ui.horizontalLayout.addWidget(self.ui.pageFrame)
            self.ui.horizontalLayout.addWidget(self.ui.revealBox0)
            self.ui.horizontalLayout.addWidget(self.ui.hideableBox)
        else:
            self.ui.horizontalLayout.addWidget(self.ui.hideableBox)
            self.ui.horizontalLayout.addWidget(self.ui.revealBox0)
            self.ui.horizontalLayout.addWidget(self.ui.pageFrame)

        load_tools(self.mouseHand)

        self.ui.deltaButton.setVisible(False)
        self.ui.ebLayout.addWidget(self.ui.modeLabel)
        self.ui.modeLayout.addWidget(self.ui.hamMenuButton)
        self.ui.modeLayout.addWidget(self.ui.finishedButton)
        self.ui.finishedButton.setMaximumWidth(16777215)  # back to default
        self.ui.modeLayout.addWidget(self.ui.finishNoRelaunchButton)
        self.ui.buttonsLayout.addWidget(self.ui.markLabel)
        self.ui.buttonsLayout.addWidget(self.ui.zoomCB)

    def viewWholePaper(self):
        """
        Changes view layout to show entire paper.

        If paper has not been opened, downloads it by it's tgvID and shows.

        Returns:
            None: modifies self.testView
        """
        # grab the files if needed.
        testNumber = self.tgvID[:4]
        if self.testViewFiles is None:
            log.debug("wholePage: downloading files for testnum {}".format(testNumber))
            (
                self.pageData,
                self.testViewFiles,
            ) = self.parentMarkerUI.downloadWholePaper(testNumber)

        # if we haven't built a testview, built it now
        if self.testView is None:
            self.testView = OriginalScansViewer(
                self, testNumber, self.pageData, self.testViewFiles
            )
        self.testView.show()
        return

    def rearrangePages(self):
        """Rearranges pages in UI.

        Returns:
            None
        """
        self.parentMarkerUI.Qapp.setOverrideCursor(Qt.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.parentMarkerUI.Qapp.processEvents()
        testNumber = self.tgvID[:4]
        # TODO: maybe download should happen in Marker?
        # TODO: all ripe for refactoring as the src_img_data improves
        image_md5_list = [x["md5"] for x in self.src_img_data]
        # note we'll md5 match within one paper only: low birthday probability
        md5_to_file_map = {x["md5"]: x["filename"] for x in self.src_img_data}
        log.info("adjustpgs: md5-to-file map: {}".format(md5_to_file_map))
        if len(set(image_md5_list)) != len(image_md5_list):
            s = dedent(
                """
                Unexpectedly repeated md5sums: are there two identical pages
                in the current annotator?  Is it allowed?  How did it happen?\n
                Annotator's image_md5_list is {}\n
                The src_img_data is {}\n
                Consider filing a bug with this info!
                """.format(
                    image_md5_list, self.src_img_data
                )
            ).strip()
            log.error(s)
            ErrorMessage(s).exec_()
        log.debug("adjustpgs: downloading files for testnum {}".format(testNumber))
        page_data = self.parentMarkerUI.downloadWholePaperMetadata(testNumber)
        for x in image_md5_list:
            if x not in [p[1] for p in page_data]:
                s = dedent(
                    """
                    Unexpectedly situation!\n
                    There is an image being annotated that is not present in
                    the server's page data.  Probably that is not allowed(?)
                    How did it happen?\n
                    Annotator's src img data is: {}\n
                    Server page_data is:
                      {}\n
                    Consider filing a bug with this info!
                    """.format(
                        self.src_img_data, page_data
                    )
                ).strip()
                log.error(s)
                ErrorMessage(s).exec_()
        # Crawl over the page_data, append a filename for each file
        # download what's needed but avoid re-downloading duplicate files
        # TODO: could defer downloading to background thread of dialog
        page_adjuster_downloads = []
        for (i, p) in enumerate(page_data):
            md5 = p[1]
            image_id = p[-1]
            fname = md5_to_file_map.get(md5)
            if fname:
                log.info(
                    "adjustpgs: not downloading image id={}; we have it already at i={}, {}".format(
                        image_id, i, fname
                    )
                )
            else:
                tmp = self.parentMarkerUI.downloadOneImage(self.tgvID, image_id, md5)
                # TODO: wrong to put these in the paperdir (?)
                # Maybe Marker should be doing this downloading
                workdir = self.parentMarkerUI.workingDirectory
                fname = tempfile.NamedTemporaryFile(
                    dir=workdir,
                    prefix="adj_pg_{}_".format(i),
                    suffix=".image",
                    delete=False,
                ).name
                log.info(
                    'adjustpages: writing "{}" from id={}, md5={}'.format(
                        fname, image_id, md5
                    )
                )
                with open(fname, "wb") as f:
                    f.write(tmp)
                assert md5_to_file_map.get(md5) is None
                md5_to_file_map[md5] = fname
                page_adjuster_downloads.append(fname)
            p.append(fname)

        is_dirty = self.scene.areThereAnnotations()
        log.debug("page_data is\n  {}".format("\n  ".join([str(x) for x in page_data])))
        rearrangeView = RearrangementViewer(
            self, testNumber, self.src_img_data, page_data, is_dirty
        )
        self.parentMarkerUI.Qapp.restoreOverrideCursor()
        if rearrangeView.exec_() == QDialog.Accepted:
            perm = rearrangeView.permute
            log.debug("adjust pages permutation output is: {}".format(perm))
        else:
            perm = None
        # Workaround for memory leak Issue #1322, TODO better fix
        rearrangeView.listA.clear()
        rearrangeView.listB.clear()
        del rearrangeView
        if perm:
            md5_tmp = [x[0] for x in perm]
            if len(set(md5_tmp)) != len(md5_tmp):
                s = dedent(
                    """
                    Unexpectedly repeated md5sums: did Adjust Pages somehow
                    dupe a page?  This should not happen!\n
                    Please file an issue with this info!\n
                    perm = {}\n
                    annotr src_img_data = {}\n
                    page_data = {}
                    """.format(
                        perm, self.src_img_data, page_data
                    )
                ).strip()
                log.error(s)
                ErrorMessage(s).exec_()
            stuff = self.parentMarkerUI.PermuteAndGetSamePaper(self.tgvID, perm)
            ## TODO: do we need to do this?
            ## TODO: before or after stuff = ...?
            # closeCurrentTGV(self)
            # TODO: possibly md5 stuff broken here too?
            log.debug("permuted: new stuff is {}".format(stuff))
            self.loadNewTGV(*stuff)
        # CAREFUL, wipe only those files we created
        # TODO: consider a broader local caching system
        for f in page_adjuster_downloads:
            os.unlink(f)
        self.setEnabled(True)
        return

    def doneViewingPaper(self):
        """
        Performs end tasks to close the Paper and view next.

        Notes:
            Called when user is done with testViewFiles.
            Adds the action to log.debug and informs self.parentMarkerUI.

        Returns:
            None: Modifies self.testView
        """
        if self.testViewFiles:
            log.debug("wholePage: done with viewFiles {}".format(self.testViewFiles))
            # could just delete them here but maybe Marker wants to cache
            self.parentMarkerUI.doneWithWholePaperFiles(self.testViewFiles)
            self.testViewFiles = None
        if self.testView:
            self.testView.close()
            self.testView = None

    def keyPopUp(self):
        """ Sets KeyPress shortcuts. """
        kp = KeyHelp()
        # Pop it up.
        kp.exec_()

    def setViewAndScene(self):
        """
        Makes a new scene (pagescene object) and connects it to the view (pageview object).

        The pageview (which is a qgraphicsview) which is (mostly) a layer
        between the annotation widget and the graphics scene which
        actually stores all the graphics objects (the image, lines, boxes,
        text etc etc). The view allows us to zoom pan etc over image and
        its annotations.

        Returns:
            None: modifies self.scene from None to a pagescene object and connects it to a pageview object.
        """
        self.scene = PageScene(
            self,
            self.src_img_data,
            self.saveName,
            self.maxMark,
            self.score,
            self.question_num,
            self.markStyle,
        )
        # connect view to scene
        self.view.connectScene(self.scene)
        # scene knows which views are connected via self.views()
        log.debug("Scene has this list of views: {}".format(self.scene.views()))

    def swapMaxNorm(self):
        """
        Toggles the window size between max and normal.

        Returns
             None: modifies self.windowState
        """
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def keyToChangeMark(self, buttonNumber):
        """
        Translates a key-press into a button-press.

        Notes:
            Each key clicks one of the delta-mark buttons in the mark-entry widget.
            If mark-up style then they trigger the positive mark buttons,
            hence p0,p1 etc... if mark down then triggers the negative mark
            buttons - n1,n2, etc.

        Returns:
            None: modifies self.markHandler.

        """
        # if key is higher than maxMark then no such button.
        if buttonNumber > self.maxMark:
            return
        # Otherwise click the appropriate button.
        self.markHandler.markButtons[buttonNumber].animateClick()

    def keyPressEvent(self, event):
        """
        Translates a key press into tool-button press if appropriate.

        Notes:
            This overrides the QWidget keyPressEvent method.

        Args:
            event(QKeyEvent): a key event (a key being pressed or released)

        Returns:
            None: modifies self

        """
        # Check to see if no mousebutton pressed
        # If a key-press detected use the keycodes dict to translate
        # the press into a function call (if exists)
        if QGuiApplication.mouseButtons() == Qt.NoButton:
            self.key_codes.get(event.key(), lambda *args: None)()
        super().keyPressEvent(event)

    def setToolMode(self, newMode, newCursor, imagePath=None):
        """
        Changes the current tool mode and cursor.

        Notes:
            TODO: this does various other mucking around for legacy
            reasons: could probably still use some refactoring.

        Returns:
            None: Modifies self
        """
        # A bit of a hack to take care of comment-mode and delta-mode
        if self.scene and self.scene.mode == "comment" and newMode != "comment":
            self.comment_widget.CL.setStyleSheet("")
        # We have to be a little careful since not all widgets get the styling in the same way.
        # If the mark-handler widget sent us here, it takes care of its own styling - so we update the little tool-tip

        if self.sender() in self.markHandler.getButtonList():
            # has come from mark-change button, markHandler does its own styling
            pass
        elif self.sender() in self.ui.frameTools.children():
            # tool buttons change the mode
            self.sender().setChecked(True)
            self.markHandler.clearButtonStyle()
        elif self.sender() is self.comment_widget.CL:
            self.markHandler.clearButtonStyle()
            self.comment_widget.CL.setStyleSheet(self.currentButtonStyleOutline)
            self.ui.commentButton.setChecked(True)
        elif self.sender() is self.markHandler:
            # Clear the style of the mark-handler (this will mostly not do
            # anything, but saves us testing if we had styled it)
            self.markHandler.clearButtonStyle()
            # this should not happen
        else:
            # this should also not happen - except by strange async race issues. So we don't change anything.
            pass

        if imagePath is not None:
            self.scene.tempImagePath = imagePath

        # pass the new mode to the graphicsview, and set the cursor in view
        if self.scene:
            self.scene.setToolMode(newMode)
            self.view.setCursor(newCursor)
            # set the modelabel
            self.ui.modeLabel.setText(" {} ".format(self.scene.mode))
        # refresh everything.
        self.repaint()

    def setIcon(self, toolButton, iconName, absoluteIconPath):
        """
        Sets a name and svg icon for a given QToolButton.

        Args:
            toolButton (QToolButton): the ui Tool Button for a name and icon to be added to.
            iconName (str): a name defining toolButton.
            absoluteIconPath (str): the absolute path to the icon for toolButton.

        Returns:
            None: alters toolButton
        """
        toolButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolButton.setToolTip("{}".format(tipText.get(iconName, iconName)))
        toolButton.setIcon(QIcon(QPixmap(absoluteIconPath)))
        toolButton.setIconSize(QSize(40, 40))

    def setAllIcons(self):
        """
        Sets all icons for the ui Tool Buttons.

        Does this by:
            1. Reads the path to PyInstaller's temporary folder through sys._MEIPASS
               More info at: https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
            2. calls the setIcon method using step 1's path to set the Icon path.

        Returns:
            None: Modifies ui Tool Buttons.
        """
        try:
            base_path = sys._MEIPASS
        except Exception:
            # a hack - fix soon.
            base_path = os.path.join(os.path.dirname(__file__), "icons")
            # base_path = "./icons"

        self.setIcon(
            self.ui.boxButton, "box", "{}/rectangle_highlight.svg".format(base_path)
        )
        self.setIcon(self.ui.commentButton, "com", "{}/comment.svg".format(base_path))
        self.setIcon(
            self.ui.commentDownButton,
            "com down",
            "{}/comment_down.svg".format(base_path),
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
        """ Saves the current annotations, and moves on to the next paper. """
        if self.scene:
            if not self.saveAnnotations():
                return
            log.debug("We have surrendered {}".format(self.tgvID))
            oldtgv = self.tgvID
            self.closeCurrentTGV()
        else:
            oldtgv = None
        stuff = self.parentMarkerUI.getMorePapers(oldtgv)
        if not stuff:
            ErrorMessage("No more to grade?").exec_()
            # Not really safe to give it back? (at least we did the view...)
            return
        log.debug("saveAndGetNext: new stuff is {}".format(stuff))
        self.loadNewTGV(*stuff)

    @pyqtSlot()
    def saveAndClose(self):
        """
        Save the current annotations, and then close.

        Returns:
            None: alters self.scene
        """
        if self.scene and not self.saveAnnotations():
            return
        self._priv_force_close = True
        self.close()

    def setMiscShortCuts(self):
        """
        Sets miscellaneous shortcuts.

        Returns:
            None: adds shortcuts.

        """
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

        self.scaleAnnotIncShortCut = QShortcut(QKeySequence("Shift+]"), self)
        self.scaleAnnotIncShortCut.activated.connect(
            lambda: self.change_annot_scale(1.1)
        )
        self.scaleAnnotDecShortCut = QShortcut(QKeySequence("Shift+["), self)
        self.scaleAnnotDecShortCut.activated.connect(
            lambda: self.change_annot_scale(1 / 1.1)
        )

        # shortcuts for undo/redo
        self.undoShortCut = QShortcut(QKeySequence("Ctrl+z"), self)
        self.undoShortCut.activated.connect(self.undo)
        self.redoShortCut = QShortcut(QKeySequence("Ctrl+y"), self)
        self.redoShortCut.activated.connect(self.redo)

        self.twisterShortCut = QShortcut(QKeySequence("Ctrl+r"), self)
        self.twisterShortCut.activated.connect(self.rearrangePages)

        # pan shortcuts
        self.panShortCut = QShortcut(QKeySequence("space"), self)
        self.panShortCut.activated.connect(self.view.panThrough)
        self.depanShortCut = QShortcut(QKeySequence("Shift+space"), self)
        self.depanShortCut.activated.connect(self.view.depanThrough)
        self.slowPanShortCut = QShortcut(QKeySequence("Ctrl+space"), self)
        self.slowPanShortCut.activated.connect(lambda: self.view.panThrough(0.02))
        self.slowDepanShortCut = QShortcut(QKeySequence("Ctrl+Shift+space"), self)
        self.slowDepanShortCut.activated.connect(lambda: self.view.depanThrough(0.02))

    def undo(self):
        """ Undoes the last action in the UI. """
        self.scene.undo()

    def redo(self):
        """ Redoes the last action in the UI. """
        self.scene.redo()

    # Simple mode change functions
    def boxMode(self):
        """ Changes the tool to box. """
        self.setToolMode("box", self.cursorBox)

    def commentMode(self):
        """ Changes the tool to comment."""
        if self.scene.mode == "comment":
            self.comment_widget.nextItem()
        else:
            self.comment_widget.currentItem()
        self.comment_widget.CL.handleClick()

    def crossMode(self):
        """ Changes the tool to crossMode. """
        self.setToolMode("cross", self.cursorCross)

    def deleteMode(self):
        """ Changes the tool to delete. """
        self.setToolMode("delete", self.cursorDelete)

    def deltaButtonMode(self):
        """ Changes the tool to the delta button. """
        if QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier:
            self.ui.deltaButton.showMenu()
        else:
            self.setToolMode("delta", Qt.ArrowCursor)

    def lineMode(self):
        """ Changes the tool to the line button.  """
        self.setToolMode("line", self.cursorLine)

    def moveMode(self):
        """ Changes the tool to the move button. """
        self.setToolMode("move", Qt.OpenHandCursor)

    def panMode(self):
        """ Changes the tool to the pan button. """
        self.setToolMode("pan", Qt.OpenHandCursor)
        # The pan button also needs to change dragmode in the view
        self.view.setDragMode(1)

    def penMode(self):
        """ Changes the tool to the pen button. """
        self.setToolMode("pen", self.cursorPen)

    def textMode(self):
        """ Changes the tool to the text button. """
        self.setToolMode("text", Qt.IBeamCursor)

    def tickMode(self):
        """ Changes the tool to the tick button. """
        self.setToolMode("tick", self.cursorTick)

    def zoomMode(self):
        """ Changes the tool to the zoom button. """
        self.setToolMode("zoom", Qt.SizeFDiagCursor)

    def loadModeFromBefore(self, mode, aux=None):
        """
        Loads mode from previous.

        Args:
            mode (str): String corresponding to the toolMode to be loaded
            aux (int) : the row of the current comment if applicable.

        Returns:

        """
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
            # make sure that the mark handler has been set.
            self.markHandler.loadDeltaValue(aux)
        elif mode == "comment" and aux is not None:
            self.comment_widget.setCurrentItemRow(aux)
            self.ui.commentButton.animateClick()
        else:
            self.loadModes.get(mode, lambda *args: None)()

    def addImageMode(self):
        """
        Opens a file dialog for images, shows a message box if the image is
        too large, otherwise continues to image mode.

        Notes:
            If the Image is greater than 200kb, will return an error.

        Returns:
            None
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "/home",
            "Image files (*.jpg *.gif " "*.png " "*.xpm" ")",
        )
        if not os.path.isfile(fileName):
            return
        if os.path.getsize(fileName) > 200000:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Image Too large.")
            msg.setText(
                "Max image size (200kB) reached. Please try again "
                "with a smaller image."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
        else:
            self.setToolMode("image", Qt.ClosedHandCursor, fileName)

    def setButtons(self):
        """ Connects buttons to their corresponding functions. """
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
        self.ui.undoButton.clicked.connect(self.undo)
        self.ui.redoButton.clicked.connect(self.redo)
        # TODO: messy viz hacks
        self.ui.cancelButton.setVisible(False)

        # Cancel button closes annotator(QDialog) with a 'reject' via the cleanUpCancel function
        self.ui.cancelButton.clicked.connect(self.close)

        # Connect the comment buttons to the comment list
        # They select the item and trigger its handleClick which fires
        # off a commentSignal which will be picked up by the annotator
        # First up connect the comment list's signal to the annotator's
        # handle comment function.
        self.comment_widget.CL.commentSignal.connect(self.handleComment)
        # Now connect up the buttons
        self.ui.commentButton.clicked.connect(self.comment_widget.currentItem)
        self.ui.commentButton.clicked.connect(self.comment_widget.CL.handleClick)
        # the previous comment button
        self.ui.commentUpButton.clicked.connect(self.comment_widget.previousItem)
        self.ui.commentUpButton.clicked.connect(self.comment_widget.CL.handleClick)
        # the next comment button
        self.ui.commentDownButton.clicked.connect(self.comment_widget.nextItem)
        self.ui.commentDownButton.clicked.connect(self.comment_widget.CL.handleClick)
        # Connect up the finishing buttons
        self.ui.finishedButton.clicked.connect(self.saveAndGetNext)
        self.ui.finishNoRelaunchButton.clicked.connect(self.saveAndClose)
        self.ui.noAnswerButton.clicked.connect(self.noAnswer)
        self.ui.rearrangePagesButton.clicked.connect(self.rearrangePages)

    def handleComment(self, dlt_txt):
        """
        Handles comments by passing the comment's delta value and text to self.scene.

        Args:
            dlt_txt (tuple [double, string] ): consists of a number corresponding to the delta for
                               the comment, followed by a string with it's corresponding text.
                               Ex:  for a +1 comment with text "forgot the chain rule"
                                    [1, "forgot the chain rule"]

        Returns:
            None: Modifies self.scene and self.toolMode

        """
        # Set the model to text and change cursor.
        self.setToolMode("comment", QCursor(Qt.IBeamCursor))
        if self.scene:  # TODO: not sure why, Issue #1283 workaround
            self.scene.changeTheComment(dlt_txt[0], dlt_txt[1], annotatorUpdate=True)

    def totalMarkSet(self, tm):
        """
        Sets the total mark and passes that info to the comment list.

        Args:
            tm (double) : the total mark of the paper.

        Returns:
            None: modifies self.scoree and self.scene.

        """
        self.score = tm
        self.comment_widget.changeMark(self.score)
        # also tell the scene what the new mark is
        if self.scene:  # TODO: bit of a hack
            self.scene.setTheMark(self.score)

    def deltaMarkSet(self, dm):
        """
        Handles when the delta button, or a comment is clicked.
        Proceeds to set set the scene and view based on the current
        delta.

        Args:
            dm (double): the positive or negative value corresponding
                           to the delta change in mark.

        Notes:
            The delta will be checked for "legality" (i.e. will the delta
             cause the grade to go below zero or above the max) at a later
             date. This will not cause the method to break.

        Returns:
            None: Modifies self.scene

        """
        if not self.scene:
            return
        self.setToolMode("delta", QCursor(Qt.IBeamCursor))
        if not self.scene.changeTheDelta(dm, annotatorUpdate=True):
            # If it is out of range then change mode to "move" so that
            # the user cannot paste in that delta.
            self.ui.moveButton.animateClick()
            return
        # Else, the delta is now set, so now change the mode here.
        self.setToolMode("delta", QCursor(Qt.IBeamCursor))
        self.ui.deltaButton.setChecked(True)

    def changeMark(self, mark):
        """
        Updates the mark-handler.

        Args:
            mark: the new mark for the given tgv.

        Returns:
            None: modifies self.score, self.ui and self.markHandler

        """
        # Tell the mark-handler what the new mark is and force a repaint.
        assert self.markStyle != 1, "Should not be called if mark-total"

        self.score = mark
        # update the markline
        self.ui.markLabel.setText(
            "{} out of {}".format(self.scene.score, self.scene.maxMark)
        )
        self.markHandler.setMark(self.score)
        self.markHandler.repaint()
        self.markHandler.updateRelevantDeltaActions()

    def loadWindowSettings(self):
        """ Loads the window settings. """
        # load the window geometry, else maximise.
        if self.parentMarkerUI.annotatorSettings["geometry"] is not None:
            self.restoreGeometry(self.parentMarkerUI.annotatorSettings["geometry"])
        else:
            self.showMaximized()

        # remember the "do not show again" checks
        if self.parentMarkerUI.annotatorSettings["markWarnings"] is not None:
            self.markWarn = self.parentMarkerUI.annotatorSettings["markWarnings"]
        if self.parentMarkerUI.annotatorSettings["commentWarnings"] is not None:
            self.commentWarn = self.parentMarkerUI.annotatorSettings["commentWarnings"]

        # remember the last tool used
        if self.parentMarkerUI.annotatorSettings["tool"] is not None:
            if self.parentMarkerUI.annotatorSettings["tool"] == "delta":
                dlt = self.parentMarkerUI.annotatorSettings["delta"]
                self.loadModeFromBefore("delta", dlt)
            elif self.parentMarkerUI.annotatorSettings["tool"] == "comment":
                cmt = self.parentMarkerUI.annotatorSettings["comment"]
                self.loadModeFromBefore("comment", cmt)
            else:
                self.loadModeFromBefore(self.parentMarkerUI.annotatorSettings["tool"])

        # if zoom-state is none, set it to index 1 (fit page) - but delay.
        if self.parentMarkerUI.annotatorSettings["zoomState"] is None:
            QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(1))
        elif self.parentMarkerUI.annotatorSettings["zoomState"] == 0:
            # is set to "user", so set the view-rectangle
            if self.parentMarkerUI.annotatorSettings["viewRectangle"] is not None:
                QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(0))
                QTimer.singleShot(
                    200,
                    lambda: self.view.initializeZoom(
                        self.parentMarkerUI.annotatorSettings["viewRectangle"]
                    ),
                )
            else:
                # no view-rectangle, so set to "fit-page"
                QTimer.singleShot(200, lambda: self.ui.zoomCB.setCurrentIndex(1))
        else:
            QTimer.singleShot(
                200,
                lambda: self.ui.zoomCB.setCurrentIndex(
                    self.parentMarkerUI.annotatorSettings["zoomState"]
                ),
            )
        # wide vs compact
        if self.parentMarkerUI.annotatorSettings["compact"] is True:
            log.debug("compacting UI (b/c of last use setting")
            self.toggleTools()

    def saveWindowSettings(self):
        """
        saves current window settings

        Returns:
            None: modifies self.parentMarkerUI and self.scene

        """
        self.parentMarkerUI.annotatorSettings["geometry"] = self.saveGeometry()
        self.parentMarkerUI.annotatorSettings[
            "viewRectangle"
        ] = self.view.getCurrentViewRect()
        self.parentMarkerUI.annotatorSettings["markWarnings"] = self.markWarn
        self.parentMarkerUI.annotatorSettings["commentWarnings"] = self.commentWarn
        self.parentMarkerUI.annotatorSettings[
            "zoomState"
        ] = self.ui.zoomCB.currentIndex()
        self.parentMarkerUI.annotatorSettings["tool"] = self.scene.mode
        if self.scene.mode == "delta":
            self.parentMarkerUI.annotatorSettings["delta"] = self.scene.markDelta
        if self.scene.mode == "comment":
            self.parentMarkerUI.annotatorSettings[
                "comment"
            ] = self.comment_widget.getCurrentItemRow()

        if self.ui.hideableBox.isVisible():
            self.parentMarkerUI.annotatorSettings["compact"] = False
        else:
            self.parentMarkerUI.annotatorSettings["compact"] = True

    def saveAnnotations(self):
        """
        Try to save the annotations and signal Marker to upload them.

        Notes:
            There are various sanity checks and user interaction to be
            done.  Return `False` if user cancels.  Return `True` if we
            should move on (for example, to close the Annotator).

            Be careful of a score of 0 - when mark total or mark up.
            Be careful of max-score when marking down.
            In either case - get user to confirm the score before closing.
            Also confirm various "not enough feedback" cases.

        Returns:
            False if user cancels, True if annotator is closed successfully.

        """
        # do some checks before accepting things
        if not self.scene.areThereAnnotations():
            msg = ErrorMessage("Please make an annotation, even if there is no answer.")
            msg.exec_()
            return False

        # check annotations are inside the margins
        if not self.scene.checkAllObjectsInside():
            msg = ErrorMessage(
                "Some annotations are outside the margins. Please move or delete them before saving."
            )
            msg.exec_()
            return False

        # warn if points where lost but insufficient annotations
        if (
            self.commentWarn
            and 0 < self.score < self.maxMark
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

        if self.score == 0 and self.markHandler.style != "Down":
            if not self._zeroMarksWarn():
                return False

        if self.score == self.maxMark and self.markHandler.style == "Down":
            if not self._fullMarkWarn():
                return False

        self.scene.save()
        self.saveMarkerComments()
        self.pickleIt()  # Pickle the scene as a plom-file

        # TODO: we should assume its dead?  Or not... let it be and fix scene?
        self.view.setHidden(True)

        # Save the current window settings for next time annotator is launched
        self.saveWindowSettings()
        try:
            self.comment_widget.saveComments()
        except (PermissionError, FileNotFoundError) as e:
            msg = ErrorMessage(
                "Error when saving local comment list:\n\n{}\n\n"
                "You may continue, but comments will not be saved "
                "between Plom instances".format(e)
            )
            msg.exec_()

        log.debug("emitting accept signal")
        tim = self.timer.elapsed() // 1000

        # some things here hardcoded elsewhere too, and up in marker
        plomFile = self.saveName[:-3] + "plom"
        commentFile = self.saveName[:-3] + "json"
        stuff = [
            self.score,
            tim,
            self.paperDir,
            self.saveName,
            plomFile,
            commentFile,
            self.integrity_check,
            self.src_img_data,
        ]
        self.annotator_upload.emit(self.tgvID, stuff)
        return True

    def _zeroMarksWarn(self):
        """
        A helper method for saveAnnotations.

        Controls warnings for when paper has 0 marks.

        Returns:
            False if user cancels, True otherwise.

        """
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
        return True

    def _fullMarkWarn(self):
        """
        A helper method for saveAnnotations.

        Controls warnings for when paper has full marks.

        Returns:
            False if user cancels, True otherwise.

        """
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

        return True

    def closeEvent(self, event):
        """
        Overrides QWidget.closeEvent().

        Deal with various cases of window trying to close.

        Notes:
        These include:
          * User closes window via titlebar close icon (or alt-f4 or...)
          * User clicks "Cancel"
          * User clicks "Done"
        Window close or Cancel are currently treated the same way:
        discard all annotations.

        Args:
            event: the event of the window closing.

        Returns:
            None: modifies many instance vars.
        """
        log.debug("========CLOSE EVENT======: {}".format(self))
        # weird hacking to force close if we came from saving.
        # Appropriate signals have already been sent so just close
        force = getattr(self, "_priv_force_close", False)
        if force:
            log.debug("emitting the closing signal")
            self.annotator_done_closing.emit(self.tgvID)
            event.accept()
            return

        # We are here b/c of cancel button, titlebar close, or related
        if self.scene and self.scene.areThereAnnotations():
            msg = SimpleMessage(
                "<p>There are annotations on the page.</p>\n"
                "<p>Do you want to discard them and close the annotator?</p>"
            )
            if msg.exec_() == QMessageBox.No:
                event.ignore()
                return
        log.debug("emitting reject/cancel signal, discarding, and closing")
        self.annotator_done_reject.emit(self.tgvID)
        # clean up after a testview
        self.doneViewingPaper()
        event.accept()

    def getComments(self):
        """ Retrieves comments from self.scene. """
        return self.scene.getComments()

    def saveMarkerComments(self):
        """ Saves the markers current comments as a commentFile. """
        commentList = self.getComments()
        # savefile is <blah>.png, save comments as <blah>.json
        with open(self.saveName[:-3] + "json", "w") as commentFile:
            json.dump(commentList, commentFile)

    def latexAFragment(self, txt):
        """
        Handles Latex text.

        Args:
            txt: the text to be Latexed

        Returns:
            None: modifies self.parentMarkerUI

        """
        return self.parentMarkerUI.latexAFragment(txt)

    def pickleIt(self):
        """
        Pickles the current page and saves it as a .plom file.
        1. Retrieves current scene items
        2. Reverses list such that newest items show last
        3. Saves pickled file as a .plom file
        4. Adds a dictionary of current Plom Data to the .plom file.

        Returns:
            None: builds a .plom file.

        """
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        # TODO: consider saving colour only if not red?
        # TODO: someday src_img_data may have other images not used
        # TODO: interleave the underlay filenames and their metadata
        plomData = {
            "fileNames": [os.path.basename(x["filename"]) for x in self.src_img_data],
            "orientations": [x["orientation"] for x in self.src_img_data],
            "saveName": os.path.basename(self.saveName),
            "markStyle": self.markStyle,
            "maxMark": self.maxMark,
            "currentMark": self.score,
            "sceneScale": self.scene.get_scale_factor(),
            "annotationColor": self.scene.ink.color().getRgb()[:3],
            "sceneItems": lst,
        }
        # save pickled file as <blah>.plom
        plomFile = self.saveName[:-3] + "plom"
        with open(plomFile, "w") as fh:
            json.dump(plomData, fh, indent="  ")
            fh.write("\n")

    def unpickleIt(self, plomData):
        """
        Unpickles the page by calling scene.unpickleSceneItems and sets
        the page's mark.

        Args:
            plomData (dict): a dictionary containing the data for the
                                pickled .plom file.

        Returns:
            None: modifies self.mark

        """
        self.view.setHidden(True)
        if plomData.get("sceneScale", None):
            self.scene.set_scale_factor(plomData["sceneScale"])
        if plomData.get("annotationColor", None):
            self.scene.set_annotation_color(plomData["annotationColor"])
        self.scene.unpickleSceneItems(plomData["sceneItems"])
        # if markstyle is "Total", then click appropriate button
        if self.markStyle == 1:
            self.markHandler.unpickleTotal(plomData["currentMark"])
        self.view.setHidden(False)

    def setZoomComboBox(self):
        """
        Sets the combo box for the zoom method.

        Returns:
            None: Modifies self.ui

        """
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
        """
        Sets the zoom ui text when user has selected "Fit Width."

        Returns:
            None: Modifies self.ui
        """
        return self.ui.zoomCB.currentText() == "Fit width"

    def isZoomFitHeight(self):
        """
        Sets the zoom ui text when user has selected "Fit Height."

        Returns:
            None: Modifies self.ui

        """
        return self.ui.zoomCB.currentText() == "Fit height"

    def changeCBZoom(self, CBIndex):
        """
        Keeps zoom combo box at selected index.

        Args:
            CBIndex (int) : the current zoom Combo Box Index

        Returns:
            None: Modifies self.ui

        """
        old = self.ui.zoomCB.blockSignals(True)
        self.ui.zoomCB.setCurrentIndex(CBIndex)
        self.ui.zoomCB.blockSignals(old)

    def zoomCBChanged(self):
        """
        Modifies the page view based on the selected zoom option.

        Returns:
            None: Modifies self.ui

        """
        if self.ui.zoomCB.currentText() == "Fit page":
            self.view.zoomFitPage()
        elif self.ui.zoomCB.currentText() == "Fit width":
            self.view.zoomFitWidth()
        elif self.ui.zoomCB.currentText() == "Fit height":
            self.view.zoomFitHeight()
        elif self.ui.zoomCB.currentText() == "100%":
            self.view.zoomToScale(1)
        elif self.ui.zoomCB.currentText() == "150%":
            self.view.zoomToScale(1.5)
        elif self.ui.zoomCB.currentText() == "200%":
            self.view.zoomToScale(2)
        elif self.ui.zoomCB.currentText() == "50%":
            self.view.zoomToScale(0.5)
        elif self.ui.zoomCB.currentText() == "33%":
            self.view.zoomToScale(0.33)
        else:
            pass
        self.view.setFocus()

    def noAnswer(self):
        """
        Handles when the user selects the "No Answer Given" option
        and ensures the user has not assigned deltas on the page. If
        deltas have been assigned, displays an error message.

        Returns:
            None

        """
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
