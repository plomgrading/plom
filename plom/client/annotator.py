# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022 Joey Shi
# Copyright (C) 2022 Natalia Accomazzo Scotti

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import json
import logging
from pathlib import Path
import os
import re
import sys
from textwrap import dedent

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QElapsedTimer,
    pyqtSlot,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QCursor,
    QIcon,
    QKeySequence,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QShortcut,
    QToolButton,
    QFileDialog,
    QColorDialog,
)
from PyQt5.QtWidgets import QGraphicsRectItem

from plom import __version__
import plom.client.cursors
import plom.client.icons
from .rubric_list import RubricWidget
from .rubrics import check_for_illadvised
from .key_wrangler import get_key_bindings
from .key_help import KeyHelp

from .pagerearranger import RearrangementViewer
from .viewers import SolutionViewer, WholeTestView, CatViewer, PreviousPaperViewer
from .pagescene import PageScene
from .pageview import PageView
from .uiFiles.ui_annotator import Ui_annotator
from .useful_classes import ErrorMsg, WarnMsg, InfoMsg
from .useful_classes import SimpleQuestion, SimpleQuestionCheckBox
from .about_dialog import show_about_dialog


log = logging.getLogger("annotr")

# Short descriptions of each tool to display to user.
tipText = {
    "box": "Box: L = highlighted box, R/Shift = highlighted ellipse.",
    "rubric": "Rubric: L = paste rubric, R/Shift = labelled box",
    "cross": "Cross: L = cross, M/Ctrl = ?-mark, R/Shift = checkmark.",
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

    def __init__(self, username, parentMarkerUI=None, initialData=None):
        """
        Initializes a new annotator window.

        Args:
            username (str): username of Marker
            parentMarkerUI (MarkerClient): the parent of annotator UI.
            initialData (dict): as documented by the arguments to "loadNewTGV"
        """
        super().__init__()

        self.username = username
        self.parentMarkerUI = parentMarkerUI
        self.tgvID = None

        # Show warnings or not
        self.markWarn = True
        self.rubricWarn = True

        # a solution view / previous annotation pop-up window - initially set to None
        self.solutionView = None

        self.testName = None
        self.paperDir = None
        self.src_img_data = None
        self.saveName = None
        self.maxMark = None

        self.ui = Ui_annotator()

        # Set up the gui.
        self.ui.setupUi(self)

        # ordered list of minor mode tools, must match the UI order
        self._list_of_minor_modes = ["box", "tick", "cross", "text", "line", "pen"]
        # current or last used tool, tracked so we can switch back
        self._which_tool = self._list_of_minor_modes[0]

        # hide the "revealbox" which is revealed when the hideBox is hidden.
        self.ui.revealBox0.setHidden(True)
        self.wideLayout()

        # Set up the graphicsview and graphicsscene of the group-image
        # loads in the image etc
        self.view = PageView(self)
        self.ui.pageFrameGrid.addWidget(self.view, 1, 1)

        # Create the rubric list widget and put into gui.
        self.rubric_widget = RubricWidget(self)
        self.ui.container_rubricwidget.addWidget(self.rubric_widget, 2)

        # pass the marking style to the rubric-widget
        # also when we set this up we have to connect various
        # mark set, mark change functions
        self.scene = None  # TODO?

        # set the zoom combobox
        self.setZoomComboBox()
        # Set the tool icons
        self.setAllIcons()
        # Set up cursors
        self.loadCursors()
        # set up held_crop_rectangle - if none, then not holding.
        self.held_crop_rectangle_data = None

        # Connect all the buttons to relevant functions
        self.setButtons()
        # Make sure window has min/max buttons.
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint
        )

        self.timer = QElapsedTimer()

        self.modeInformation = ["move"]

        if initialData:
            self.loadNewTGV(*initialData)

        self.rubric_widget.setInitialRubrics()

        # Grab window settings from parent
        self.loadWindowSettings()

        # no initial keybindings - get from the marker if non-default
        self.keybinding_name = self.parentMarkerUI.annotatorSettings["keybinding_name"]
        if self.keybinding_name is None:
            self.keybinding_name = "default"
            log.info('starting with default keybinding "%s"', self.keybinding_name)
        else:
            log.info('loaded previous keybinding "%s"', self.keybinding_name)
        # TODO: store this in annotatorSettings too
        self.keybinding_custom_overlay = self.parentMarkerUI.annotatorSettings[
            "keybinding_custom_overlay"
        ]
        if self.keybinding_custom_overlay is None:
            self.keybinding_custom_overlay = {}
            log.info("starting new (empty) custom overlay")
        else:
            log.info("loaded custom overlay: %s", self.keybinding_custom_overlay)

        self.ui.hamMenuButton.setMenu(self.buildHamburger())
        self.ui.hamMenuButton.setToolTip("Menu (F10)")
        self.ui.hamMenuButton.setPopupMode(QToolButton.InstantPopup)
        self.setToolShortCuts()
        self.setMinorShortCuts()

    def getScore(self):
        return self.scene.getScore()

    def toggle_hold_crop(self, checked):
        if checked:
            if not self.scene:
                # unfort. backref instance var: if no scene, prevent checking
                self._hold_crop_checkbox.setChecked(False)
                return
            self.held_crop_rectangle_data = (
                self.scene.current_crop_rectangle_as_proportions()
            )
            log.debug(f"Hold crop for upcoming pages = {self.held_crop_rectangle_data}")
        else:
            log.debug("Released crop")
            self.held_crop_rectangle_data = None

    def toggle_experimental(self, checked):
        if not checked:
            self.parentMarkerUI.set_experimental(False)
            # TODO: some kind of signal/slot, ontoggle...
            self._cat_view_menu.setVisible(False)
            self._hold_crop_checkbox.setVisible(False)
            return

        txt = """<p>Enable experimental and/or advanced options?</p>
            <p>If you are part of a large marking team, you should
            probably discuss with your manager before enabling.</p>
        """
        # features = (
        #     'None, but you can help us break stuff at <a href="https://gitlab.com/plom/plom">gitlab.com/plom/plom</a>',
        # )
        features = (
            "Creating new absolute rubrics, such as &ldquo;2 of 3&rdquo;.",
            "Creating new rubrics parameterized over version.",
            "Persistent held region between papers.",
            "Viewing cat pics.",
        )
        info = f"""
            <h4>Current experimental features</h4>
            <ul>
              {" ".join("<li>" + x + "</li>" for x in features)}
            </ul>
        """
        # Image by liftarn, public domain, https://freesvg.org/put-your-fingers-in-the-gears
        res = resources.files(plom.client.icons) / "fingers_in_gears.svg"
        pix = QPixmap()
        pix.loadFromData(res.read_bytes())
        pix = pix.scaledToHeight(256, Qt.SmoothTransformation)
        msg = SimpleQuestion(self, txt, question=info)
        msg.setIconPixmap(pix)
        if msg.exec() == QMessageBox.No:
            self._experimental_mode_checkbox.setChecked(False)
            return
        self.parentMarkerUI.set_experimental(True)
        # TODO: some kind of signal/slot, ontoggle...
        self._cat_view_menu.setVisible(True)
        self._hold_crop_checkbox.setVisible(True)

    def is_experimental(self):
        return self.parentMarkerUI.is_experimental()

    def buildHamburger(self):
        # TODO: use QAction, share with other UI?
        keydata = self.get_key_bindings()

        m = QMenu()
        key = keydata["next-paper"]["keys"][0]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Next paper\t{key}", self.saveAndGetNext)
        m.addAction("Done (save and close)", self.saveAndClose)
        m.addAction("Defer and go to next", lambda: None).setEnabled(False)
        (key,) = keydata["cancel"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Close without saving\t{key}", self.close)
        m.addSeparator()
        (key,) = keydata["quick-show-prev-paper"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Show previous paper(s)\t{key}", self.show_previous)
        m.addSeparator()
        self._cat_view_menu = m.addAction("View cat", self.viewCat)
        if not self.is_experimental():
            self._cat_view_menu.setVisible(False)
        (key,) = keydata["show-solutions"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"View solutions\t{key}", self.viewSolutions)
        (key,) = keydata["tag-paper"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Tag paper...\t{key}", self.tag_paper)
        m.addSeparator()
        (key,) = keydata["rearrange-pages"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Adjust pages\t{key}", self.rearrangePages)
        (key,) = keydata["crop-in"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Crop to region\t{key}", self.to_crop_mode)
        (key,) = keydata["crop-out"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Uncrop\t{key}", self.uncrop_region)
        hold_crop = m.addAction("Hold crop between papers")
        hold_crop.setCheckable(True)
        hold_crop.triggered.connect(self.toggle_hold_crop)
        self._hold_crop_checkbox = hold_crop
        if not self.is_experimental():
            self._hold_crop_checkbox.setVisible(False)
        m.addSeparator()
        subm = m.addMenu("Tools")
        # to make these actions checkable, they need to belong to self.
        # submg = QActionGroup(m)
        # km.addAction(getattr(self, "kb_{}_act".format(name)))
        # TODO: add selection indicator
        # TDDO: and keyboard shortcuts: how to update them?
        subm.addAction("Box", self.ui.boxButton.animateClick)
        subm.addAction("Tick", self.ui.tickButton.animateClick)
        subm.addAction("Cross", self.ui.crossButton.animateClick)
        subm.addAction("Text", self.ui.textButton.animateClick)
        subm.addAction("Line", self.ui.lineButton.animateClick)
        subm.addAction("Pen", self.ui.penButton.animateClick)
        subm.addSeparator()
        subm.addAction("Insert image", self.addImageMode)
        subm.addSeparator()
        subm.addAction("Move", self.ui.moveButton.animateClick)
        subm.addAction("Pan", self.ui.panButton.animateClick)
        subm.addAction("Delete", self.ui.deleteButton.animateClick)
        subm.addAction("Zoom", self.ui.zoomButton.animateClick)
        m.addSeparator()
        (key,) = keydata["increase-annotation-scale"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(
            f"Increase annotation scale\t{key}",
            lambda: self.change_annot_scale(1.1),
        )
        # Keep a reference to this one so we can update the text
        self._reset_scale_menu_text = "Reset annotation scale"
        self._reset_scale_QAction = m.addAction(
            self._reset_scale_menu_text, self.change_annot_scale
        )
        self.update_annot_scale_menu_label()

        (key,) = keydata["decrease-annotation-scale"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(
            f"Decrease annotation scale\t{key}",
            lambda: self.change_annot_scale(1.0 / 1.1),
        )
        # Issue #1350: temporarily?
        m.addAction(
            "Temporarily change annot. colour",
            self.change_annotation_colour,
        )
        m.addSeparator()
        x = m.addAction("Experimental features")
        x.setCheckable(True)
        if self.is_experimental():
            x.setChecked(True)
        x.triggered.connect(self.toggle_experimental)
        self._experimental_mode_checkbox = x
        m.addAction("Synchronise rubrics", self.refreshRubrics)
        (key,) = keydata["toggle-wide-narrow"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Compact UI\t{key}", self.narrowLayout)
        # TODO: this should be an indicator but for now compact doesn't have the hamburg menu
        # m.addAction("&Wide UI\thome", self.wideLayout)
        m.addSeparator()
        m.addAction("Help", lambda: self.keyPopUp(tab_idx=0))
        (key,) = keydata["help"]["keys"]
        key = QKeySequence(key).toString(QKeySequence.NativeText)
        m.addAction(f"Show shortcut keys...\t{key}", self.keyPopUp)
        m.addAction("About Plom", lambda: show_about_dialog(self))
        return m

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
        if self.scene.mode == "rubric":
            key, tab = self.rubric_widget.getCurrentRubricKeyAndTab()
            if key is None:
                # Maybe row hidden (illegal) but scene knows it in the blue
                # ghost.  Fixes #1599.  Still None if scene didn't know.
                key = self.scene.get_current_rubric_id()
            self.modeInformation.append((key, tab))

        # after grabbed mode information, reset rubric_widget
        self.rubric_widget.setEnabled(False)

        del self.scene
        self.scene = None

        self.tgvID = None
        self.testName = None
        self.setWindowTitle("Annotator")
        self.paperDir = None
        self.src_img_data = None
        self.saveName = None
        # feels like a bit of a kludge
        self.view.setHidden(True)

    def loadNewTGV(
        self,
        tgvID,
        question_label,
        version,
        max_version,
        testName,
        paperdir,
        saveName,
        maxMark,
        plomDict,
        integrity_check,
        src_img_data,
    ):
        """Loads new data into the window for marking.

        Args:
            tgvID (str): Test-Group-Version ID code.  For example, for
                Test #0027, group #13, version #2, we have `t0027g13v2`.
                TODO: currently only `t0027g13`, no version, despite name.
            question_label (str): The name of the question we are
                marking.  This is generally used for display only as
                there is an integer for precise usage.
            version (int): which version are we working on?
            max_version (int): what is the largest version in this assessment?
            testName (str): Test Name
            paperdir (dir): Working directory for the current task
            saveName (str/pathlib.Path): file name (and dir, optionally)
                of the basename to save things (no .png/.jpg extension)
                If it does have an extension, it will be *ignored*.
            maxMark (int): maximum possible score for that test question
            plomDict (dict): a dictionary of annotation information.
                Contains sufficient information to recreate the annotation
                objects on the page if you go back to continue annotating a
                question.
            integrity_check (str): integrity check string
            src_img_data (list[dict]): image md5sums, filenames etc.

        Returns:
            None: Modifies many instance vars.

        """
        self.tgvID = tgvID
        self.question_num = int(re.split(r"\D+", tgvID)[-1])
        self.version = version
        self.max_version = max_version
        self.question_label = question_label
        self.testName = testName
        s = "{} of {}: {}".format(self.question_label, testName, tgvID)
        self.setWindowTitle("{} - Plom Annotator".format(s))
        log.info("Annotating {}".format(s))
        self.paperDir = paperdir
        self.saveName = Path(saveName)
        self.integrity_check = integrity_check
        self.src_img_data = src_img_data
        self.maxMark = maxMark
        del maxMark

        if plomDict:
            assert plomDict["maxMark"] == self.maxMark, "mismatch between maxMarks"

        # Set up the graphicsview and graphicsscene of the group-image
        # loads in the image etc
        self.view.setHidden(False)  # or try not hiding it...
        self.setViewAndScene()
        # TODO: see above, can we maintain our zoom b/w images?  Would anyone want that?
        # TODO: see above, don't click a different button: want to keep same tool

        # update displayed score
        self.refreshDisplayedMark(self.getScore())
        # update rubrics
        self.rubric_widget.setQuestion(self.question_num, self.question_label)
        self.rubric_widget.setVersion(self.version, self.max_version)
        self.rubric_widget.setMaxMark(self.maxMark)
        self.rubric_widget.setEnabled(True)

        # TODO: Make handling of rubric less hack.
        log.debug("Restore mode info = {}".format(self.modeInformation))
        self.setToolMode(self.modeInformation[0])
        # TODO: refactor, see also self.handleRubric() and self.rubricMode()
        if self.modeInformation[0] == "rubric":
            extra = self.modeInformation[1]
            if self.rubric_widget.setCurrentRubricKeyAndTab(*extra):
                self.rubric_widget.handleClick()
            else:  # if that rubric-mode-set fails (eg - no such rubric)
                self.toMoveMode()
        # redo this after all the other rubric stuff initialised
        self.rubric_widget.updateLegalityOfRubrics()

        # Very last thing = unpickle scene from plomDict if there is one
        if plomDict is not None:
            self.unpickleIt(plomDict)
            # restoring the scene would've marked it dirty
            self.scene.reset_dirty()
        else:
            # if there is a held crop rectangle, then use it.
            if self.held_crop_rectangle_data:
                self.scene.crop_from_plomfile(self.held_crop_rectangle_data)

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

    def refreshDisplayedMark(self, score):
        """
        Update the marklabel (and narrow one) with the current score - triggered by pagescene

        Returns:
            None

        """
        self.ui.markLabel.setStyleSheet("color: #ff0000; font: bold;")
        self.ui.narrowMarkLabel.setStyleSheet("color: #ff0000; font: bold;")
        if score is None:
            self.ui.markLabel.setText("Unmarked")
            self.ui.narrowMarkLabel.setText("Unmarked")
        else:
            self.ui.markLabel.setText("{} out of {}".format(score, self.maxMark))
            self.ui.narrowMarkLabel.setText("{} out of {}".format(score, self.maxMark))

    def loadCursors(self):
        """Load custom cursors and set their hotspots.

        Returns:
            None
        """

        def _pixmap_from(f):
            pm = QPixmap()
            res = resources.files(plom.client.cursors) / f
            pm.loadFromData(res.read_bytes())
            return pm

        # The keys here are magic values that connect to tools
        cursor = {}
        cursor["box"] = QCursor(_pixmap_from("box.png"), 4, 4)
        cursor["ellipse"] = QCursor(_pixmap_from("ellipse.png"), 4, 4)
        cursor["cross"] = QCursor(_pixmap_from("cross.png"), 4, 4)
        cursor["crop"] = QCursor(_pixmap_from("crop.png"), 4, 4)
        cursor["delete"] = QCursor(_pixmap_from("delete.png"), 4, 4)
        cursor["line"] = QCursor(_pixmap_from("line.png"), 4, 4)
        cursor["pen"] = QCursor(_pixmap_from("pen.png"), 4, 4)
        cursor["tick"] = QCursor(_pixmap_from("tick.png"), 4, 4)
        cursor["QMark"] = QCursor(_pixmap_from("question_mark.png"), 4, 4)
        cursor["Highlight"] = QCursor(_pixmap_from("highlighter.png"), 4, 4)
        cursor["arrow"] = QCursor(_pixmap_from("arrow.png"), 4, 4)
        cursor["DoubleArrow"] = QCursor(_pixmap_from("double_arrow.png"), 4, 4)
        cursor["text"] = Qt.IBeamCursor
        cursor["rubric"] = Qt.IBeamCursor
        cursor["image"] = Qt.CrossCursor
        cursor["zoom"] = Qt.SizeFDiagCursor
        # note Qt.ClosedHandCursor and Qt.OpenHandCursor also hardcoded in pagescene
        cursor["pan"] = Qt.OpenHandCursor
        cursor["move"] = Qt.OpenHandCursor

        self.cursor = cursor

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

    def wideLayout(self):
        """
        Changes view to Wide Layout style.

        Returns:
            None: modifies self.ui
        """
        self.ui.hideableBox.show()
        self.ui.revealBox0.hide()

    def next_rubric(self):
        self.rubric_widget.nextRubric()

    def prev_rubric(self):
        self.rubric_widget.previousRubric()

    def next_tab(self):
        self.rubric_widget.next_tab()

    def prev_tab(self):
        self.rubric_widget.prev_tab()

    def next_minor_tool(self, dir=1, always_move=False):
        """Switch to current minor tool or advance to next minor tool.

        args:
            dir (int): +1 for next (default), -1 for previous.
            always_move (bool): the minor tools keep track of the
                last-used tool.  Often, but not always, we want to
                switch back to the last-used tool.  False by default.
        """
        L = self._list_of_minor_modes
        # if always-move then select the next/previous tool according to dir
        # elif in a tool-mode then select next/prev tool according to dir
        # elif - non-tool mode, so keep the last tool
        if always_move:  # set index to the last tool we used
            self._which_tool = L[(L.index(self._which_tool) + dir) % len(L)]
        elif self.scene.mode in L:
            self._which_tool = L[(L.index(self.scene.mode) + dir) % len(L)]
        else:
            pass  # keep the current tool
        getattr(self.ui, "{}Button".format(self._which_tool)).animateClick()

    def prev_minor_tool(self):
        """Switch backward to the previous minor tool."""
        self.next_minor_tool(dir=-1, always_move=True)

    def viewWholePaper(self):
        """
        Popup a dialog showing the entire paper.

        TODO: this has significant duplication with RearrangePages.

        Returns:
            None
        """
        if not self.tgvID:
            return
        testnum = self.tgvID[:4]
        log.debug("wholePage: downloading files for testnum %s", testnum)
        dl = self.parentMarkerUI.Qapp.downloader
        pagedata = dl.msgr.get_pagedata_context_question(testnum, self.question_num)
        pagedata = dl.sync_downloads(pagedata)
        labels = [x["pagename"] for x in pagedata]
        WholeTestView(testnum, pagedata, labels, parent=self).exec()

    def rearrangePages(self):
        """Rearranges pages in UI.

        Returns:
            None
        """
        if not self.tgvID or not self.scene:
            return
        self.parentMarkerUI.Qapp.setOverrideCursor(Qt.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.parentMarkerUI.Qapp.processEvents()
        testNumber = self.tgvID[:4]
        image_md5_list = [x["md5"] for x in self.src_img_data]
        # Look for duplicates by first inverting the dict
        repeats = {}
        for i, md5 in enumerate(image_md5_list):
            repeats.setdefault(md5, []).append(i)
        repeats = {k: v for k, v in repeats.items() if len(v) > 1}
        if repeats:
            log.warning("Repeated pages in md5sum data: %s", repeats)
            info = dedent(
                """
                <p>This can happen with self-submitted work if a student
                submits multiple copies of the same page.
                Its probably harmless in that case, but if you see this
                with scanned work, it might indicate a bug.</p>
                <p>The repeated pages are:</p>
                <ul>
                """
            )
            for md5, pages in repeats.items():
                info += f"<li>pages {pages} @ md5: {md5}</li>"
            info += "</ul>"
            ErrorMsg(
                self,
                "Warning: duplicate pages detected!",
                info=info,
                info_pre=False,
                details=f"Annotator's image_md5_list is\n  {image_md5_list}\n"
                f"The src_img_data is\n  {self.src_img_data}\n"
                f"Include this info if you think this is a bug!",
            ).exec()
        log.debug("adjustpgs: downloading files for testnum {}".format(testNumber))

        dl = self.parentMarkerUI.Qapp.downloader
        page_data = dl.msgr.get_pagedata_context_question(testNumber, self.question_num)
        # TODO: eventually want dialog to open during loading, Issue #2355
        N = len(page_data)
        pd = QProgressDialog(
            "Downloading additional images\nStarting up...", None, 0, N, self
        )
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(500)
        pd.setValue(0)
        self.parentMarkerUI.Qapp.processEvents()
        for i, row in enumerate(page_data):
            # TODO: would be nice to show the size in MiB here!
            pd.setLabelText(
                f"Downloading additional images\nFile {i + 1} of {N}: img id {row['id']}"
            )
            pd.setValue(i + 1)
            self.parentMarkerUI.Qapp.processEvents()
            row = dl.sync_download(row)
        pd.close()

        #
        for x in image_md5_list:
            if x not in [p["md5"] for p in page_data]:
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
                ErrorMsg(self, s).exec()

        has_annotations = self.scene.areThereAnnotations()
        log.debug("page_data is\n  {}".format("\n  ".join([str(x) for x in page_data])))
        rearrangeView = RearrangementViewer(
            self, testNumber, self.src_img_data, page_data, has_annotations
        )
        # TODO: have rearrange react to new downloads
        # PC.download_finished.connect(rearrangeView.shake_things_up)
        perm = []
        self.parentMarkerUI.Qapp.restoreOverrideCursor()
        if rearrangeView.exec() == QDialog.Accepted:
            perm = rearrangeView.permute
            log.debug("adjust pages permutation output is: {}".format(perm))
        # Workaround for memory leak Issue #1322, TODO better fix
        rearrangeView.listA.clear()
        rearrangeView.listB.clear()
        rearrangeView.deleteLater()  # disconnects slots and signals
        del rearrangeView
        if perm:
            # Sanity check for dupes in the permutation
            # pylint: disable=unsubscriptable-object
            md5 = [x["md5"] for x in perm]
            # But if the input already had dupes than its not our problem
            md5_in = [x["md5"] for x in self.src_img_data]
            if len(set(md5)) != len(md5) and len(set(md5_in)) == len(md5_in):
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
                ErrorMsg(self, s).exec()

            tmp_tgv = self.tgvID
            self.closeCurrentTGV()
            stuff = self.parentMarkerUI.PermuteAndGetSamePaper(tmp_tgv, perm)
            log.debug("permuted: new stuff is {}".format(stuff))
            if not stuff:
                txt = """
                    <p>Unexpectedly, Marker did not give us back the permuted
                    material for marking.</p>
                    <p>Something has gone wrong, maybe related to
                    <a href="https://gitlab.com/plom/plom/-/issues/1967">Issue #1967</a>.
                    </p>
                """
                ErrorMsg(self, txt).exec()
            self.loadNewTGV(*stuff)
        self.setEnabled(True)
        return

    def experimental_cycle(self):
        self.scene.whichLineToDraw_next()

    def keyPopUp(self, *, tab_idx=None):
        """View help and keyboard shortcuts, eventually edit them.

        Keyword Arg:
            tab_idx (int/None): which tab to open in the help.  If None
                then we try to re-open on the same tab from last run.
        """
        if tab_idx is None:
            _tab_idx = getattr(self, "_keyhelp_tab_idx", 0)
        else:
            _tab_idx = tab_idx
        diag = KeyHelp(
            self,
            self.keybinding_name,
            custom_overlay=self.keybinding_custom_overlay,
            initial_tab=_tab_idx,
        )
        if diag.exec() != QDialog.Accepted:
            return
        self.keybinding_name = diag.get_selected_keybinding_name()
        if self.keybinding_name == "custom":
            # note: if dialog modified custom, but then selected another
            # such as "ijkl", then we should *not* overwrite custom.
            self.keybinding_custom_overlay = diag.get_custom_overlay()
        if tab_idx is None:
            # keep the open tab for next time we re-open KeyHelp
            self._keyhelp_tab_idx = diag.tabs.currentIndex()
        self.parentMarkerUI.annotatorSettings["keybinding_name"] = self.keybinding_name
        self.parentMarkerUI.annotatorSettings[
            "keybinding_custom_overlay"
        ] = self.keybinding_custom_overlay
        self.setToolShortCuts()

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
            self.maxMark,
            self.question_label,
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

    def keyToChangeRubric(self, keyNumber):
        """
        Translates a the numerical key into a selection of that visible
        row of the current rubric tab.

        Returns:
            None: modifies self.rubric_widget
        """
        # row is one less than key
        self.rubric_widget.selectRubricByVisibleRow(keyNumber - 1)

    def setToolMode(self, newMode, *, cursor=None, imagePath=None):
        """
        Changes the current tool mode and cursor.

        Args:
            newMode (str): ``"move"``, ``"rubric"`` etc.

        Keyword Args:
            imagePath (?): an argument for the "image" tool, used
                used only by the image tool.
            cursor (str): if None or omitted default cursors are used
               for each tool.  If needed you could override this.
               (currently unused, semi-deprecated).

        Notes:
            TODO: this does various other mucking around for legacy
            reasons: could probably still use some refactoring.

        Returns:
            None: Modifies self
        """
        if cursor is None:
            cursor = self.cursor[newMode]

        if newMode == "rubric":
            self._uncheck_exclusive_group()

        # ensure`_which_tool` is updated via mouse click too, see next_minor_tool()
        if newMode in self._list_of_minor_modes:
            self._which_tool = newMode

        if self.scene and imagePath is not None:
            self.scene.tempImagePath = imagePath

        # pass the new mode to the graphicsview, and set the cursor in view
        if self.scene:
            self.scene.setToolMode(newMode)
            self.view.setCursor(cursor)
        # refresh everything.
        self.repaint()

    def setModeLabels(self, mode):
        if mode == "rubric":
            self.ui.narrowModeLabel.setText(
                " rubric \n {} ".format(self.rubric_widget.getCurrentTabName())
            )
            self.ui.wideModeLabel.setText(
                " rubric {} ".format(self.rubric_widget.getCurrentTabName())
            )
        else:
            self.ui.narrowModeLabel.setText(" {} ".format(mode))
            self.ui.wideModeLabel.setText(" {} ".format(mode))

    def setIcon(self, toolButton, name, iconfile):
        """
        Sets a name and svg icon for a given QToolButton.

        Args:
            toolButton (QToolButton): the ui Tool Button for a name and icon to be added to.
            name (str): a name defining toolButton.
            iconfile (str): filename of .svg, must be in the resource
                `plom.client.icons`.

        Returns:
            None: alters toolButton
        """
        toolButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolButton.setToolTip("{}".format(tipText.get(name, name)))
        pm = QPixmap()
        res = resources.files(plom.client.icons) / iconfile
        pm.loadFromData(res.read_bytes())
        toolButton.setIcon(QIcon(pm))
        # toolButton.setIconSize(QSize(40, 40))

    def setAllIcons(self):
        """
        Sets all icons for the ui Tool Buttons.

        Returns:
            None: Modifies ui Tool Buttons.
        """
        self.setIcon(self.ui.boxButton, "box", "rectangle_highlight.svg")
        self.setIcon(self.ui.crossButton, "cross", "cross.svg")
        self.setIcon(self.ui.deleteButton, "delete", "delete.svg")
        self.setIcon(self.ui.lineButton, "line", "line.svg")
        self.setIcon(self.ui.moveButton, "move", "move.svg")
        self.setIcon(self.ui.panButton, "pan", "pan.svg")
        self.setIcon(self.ui.penButton, "pen", "pen.svg")
        self.setIcon(self.ui.redoButton, "redo", "redo.svg")
        self.setIcon(self.ui.textButton, "text", "text.svg")
        self.setIcon(self.ui.tickButton, "tick", "tick.svg")
        self.setIcon(self.ui.undoButton, "undo", "undo.svg")
        self.setIcon(self.ui.zoomButton, "zoom", "zoom.svg")

    @pyqtSlot()
    def saveAndGetNext(self):
        """Saves the current annotations, and moves on to the next paper."""
        if self.scene:
            if not self.saveAnnotations():
                return
            log.debug("We have surrendered {}".format(self.tgvID))
            tmp_tgv = self.tgvID
            self.closeCurrentTGV()
        else:
            tmp_tgv = None

        # Workaround getting too far ahead of Marker's upload queue
        queue_len = self.parentMarkerUI.get_upload_queue_length()
        if queue_len >= 3:
            WarnMsg(
                self,
                f"<p>Plom is waiting to upload {queue_len} papers.</p>"
                + "<p>This might indicate network trouble: unfortunately Plom "
                + "does not yet deal with this gracefully and there is a risk "
                + "we might lose your non-uploaded work!</p>"
                + "<p>You should consider closing the Annotator, and waiting "
                + "a moment to see if the queue of &ldquo;uploading...&rdquo; "
                + "papers clear.</p>",
            ).exec()

        stuff = self.parentMarkerUI.getMorePapers(tmp_tgv)
        if not stuff:
            InfoMsg(self, "No more to grade?").exec()
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

    def get_key_bindings(self):
        return get_key_bindings(self.keybinding_name, self.keybinding_custom_overlay)

    def setToolShortCuts(self):
        """Set or change the shortcuts for the basic tool keys.

        These are the shortcuts that are user-editable.
        """
        keydata = self.get_key_bindings()
        actions_and_methods = (
            ("undo", self.toUndo),
            ("redo", self.toRedo),
            ("next-rubric", self.rubricMode),
            ("prev-rubric", self.prev_rubric),
            ("next-tab", self.next_tab),
            ("prev-tab", self.prev_tab),
            ("next-tool", self.next_minor_tool),
            ("prev-tool", self.prev_minor_tool),
            ("delete", self.toDeleteMode),
            ("move", self.toMoveMode),
            ("zoom", self.toZoomMode),
        )
        # wipe any existing shortcuts
        shortcuts = getattr(self, "_store_QShortcuts", [])
        for sc in shortcuts:
            sc.deleteLater()
            del sc

        # store the shortcuts to prevent GC
        self._store_QShortcuts = []
        for (action, command) in actions_and_methods:
            (key,) = keydata[action]["keys"]  # enforce single item
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(command)
            self._store_QShortcuts.append(sc)

    def setMinorShortCuts(self):
        """Setup non-editable shortcuts.

        Each of these actions can be associated with multiple shortcut
        keys.
        """
        keydata = self.get_key_bindings()
        actions_and_methods = (
            ("toggle-wide-narrow", self.toggleTools),
            ("help", self.keyPopUp),
            ("toggle-maximize-window", self.swapMaxNorm),
            ("show-whole-paper", self.viewWholePaper),
            ("show-solutions", self.viewSolutions),
            ("main-menu", self.ui.hamMenuButton.animateClick),
            ("tag-paper", self.tag_paper),
            ("zoom-in", self.view.zoomIn),
            ("zoom-out", self.view.zoomOut),
            ("next-paper", self.saveAndGetNext),
            ("cancel", self.close),
            ("toggle-zoom", self.view.zoomToggle),
            ("pan-through", self.view.panThrough),
            ("pan-back", self.view.depanThrough),
            ("pan-through-slowly", lambda: self.view.panThrough(0.02)),
            ("pan-back-slowly", lambda: self.view.depanThrough(0.02)),
            ("undo-2", self.toUndo),
            ("redo-2", self.toRedo),
            ("rearrange-pages", self.rearrangePages),
            ("quick-show-prev-paper", self.show_previous),
            ("increase-annotation-scale", lambda: self.change_annot_scale(1.1)),
            ("decrease-annotation-scale", lambda: self.change_annot_scale(1 / 1.1)),
            ("crop-in", self.to_crop_mode),
            ("crop-out", self.uncrop_region),
        )
        self._store_QShortcuts_minor = []
        for (action, command) in actions_and_methods:
            for key in keydata[action]["keys"]:
                sc = QShortcut(QKeySequence(key), self)
                sc.activated.connect(command)
            self._store_QShortcuts_minor.append(sc)

        def lambda_factory(n):
            return lambda: self.keyToChangeRubric(n)

        # rubric shortcuts
        self._store_QShortcuts_rubrics = []
        for n in range(1, 11):
            # keys 1, 2, 3, 4, 5, 6, 7, 8, 9, 0
            key = f"{n % 10}"
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda_factory(n))
            self._store_QShortcuts_rubrics.append(sc)

        # TODO: hardcoded, do we want shift-undo to be redo? Issue #2246
        self.redoShortCut2 = QShortcut(QKeySequence("Shift+g"), self)
        self.redoShortCut2.activated.connect(self.ui.redoButton.animateClick)

        self.sekritShortCut = QShortcut(QKeySequence("Ctrl+Shift+o"), self)
        self.sekritShortCut.activated.connect(self.experimental_cycle)

    def to_crop_mode(self):
        # can't re-crop if the crop is being held
        if self.held_crop_rectangle_data:
            WarnMsg(
                self,
                "You cannot re-crop while a crop is being held.",
                info="Unselect 'hold crop' from the menu and then try again.",
            ).exec()
        else:
            self.setToolMode("crop")

    def uncrop_region(self):
        if self.held_crop_rectangle_data:
            WarnMsg(
                self,
                "You cannot un-crop while a crop is being held.",
                info="Unselect 'hold crop' from the menu and then try again.",
            ).exec()
            return
        if not self.scene:
            return
        self.scene.uncrop_underlying_images()

    def toUndo(self):
        self.ui.undoButton.animateClick()

    def undo(self):
        """Undoes the last action in the UI."""
        if not self.scene:
            return
        if self.scene.isDrawing():
            self.scene.stopMidDraw()
        else:
            self.scene.undo()

    def toRedo(self):
        self.ui.redoButton.animateClick()

    def redo(self):
        """Redoes the last action in the UI."""
        if not self.scene:
            return
        self.scene.redo()

    def rubricMode(self):
        """Changes the tool to rubric."""
        if not self.scene:
            self.rubric_widget.nextRubric()
            return
        if self.scene.mode == "rubric":
            self.rubric_widget.nextRubric()
        else:
            self.rubric_widget.reselectCurrentRubric()

    def toDeleteMode(self):
        self.ui.deleteButton.animateClick()

    def toMoveMode(self):
        self.ui.moveButton.animateClick()

    def toZoomMode(self):
        self.ui.zoomButton.animateClick()

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
            "",
            "Image files (*.jpg *.gif *.png *.xpm)",
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
            self.setToolMode("image", imagePath=fileName)

    def setButtons(self):
        """Connects buttons to their corresponding functions."""
        # Connect the key-help button
        self.ui.helpButton.clicked.connect(self.keyPopUp)

        # tool buttons change the mode
        self.ui.boxButton.clicked.connect(lambda: self.setToolMode("box"))
        self.ui.crossButton.clicked.connect(lambda: self.setToolMode("cross"))
        self.ui.deleteButton.clicked.connect(lambda: self.setToolMode("delete"))
        self.ui.lineButton.clicked.connect(lambda: self.setToolMode("line"))
        self.ui.moveButton.clicked.connect(lambda: self.setToolMode("move"))
        self.ui.panButton.clicked.connect(lambda: self.setToolMode("pan"))
        self.ui.penButton.clicked.connect(lambda: self.setToolMode("pen"))
        self.ui.textButton.clicked.connect(lambda: self.setToolMode("text"))
        self.ui.tickButton.clicked.connect(lambda: self.setToolMode("tick"))
        self.ui.zoomButton.clicked.connect(lambda: self.setToolMode("zoom"))

        # Pass the undo/redo button clicks on to the view
        self.ui.undoButton.clicked.connect(self.undo)
        self.ui.redoButton.clicked.connect(self.redo)

        # Connect the rubric buttons to the rubric list
        # They select the item and trigger its handleClick which fires
        # off a rubricSignal which will be picked up by the annotator
        # First up connect the rubric list's signal to the annotator's
        # handle rubric function.
        self.rubric_widget.rubricSignal.connect(self.handleRubric)
        self.ui.rearrangePagesButton.clicked.connect(self.rearrangePages)
        # Connect up the finishing functions - using a dropdown menu
        m = QMenu()
        m.addAction("Done", self.saveAndClose)
        m.addSeparator()
        m.addAction("Cancel", self.close)
        self.ui.finishedButton.setMenu(m)
        self.ui.finishedButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.ui.finishedButton.clicked.connect(self.saveAndGetNext)

        # connect the "wide" button in the narrow-view
        self.ui.wideButton.clicked.connect(self.wideLayout)

    def _uncheck_exclusive_group(self):
        # Stupid hackery to uncheck an autoexclusive button.
        # For example, when we switch focus to the rubric_list, we want to
        # unselect all the tools.  An alternative would be somehow hacking
        # the autoexclusive property into rubric_list (its normally for
        # buttons).  Or to revert managing the button state ourselves.
        for X in (
            self.ui.boxButton,
            self.ui.crossButton,
            self.ui.deleteButton,
            self.ui.lineButton,
            self.ui.moveButton,
            self.ui.panButton,
            self.ui.penButton,
            self.ui.textButton,
            self.ui.tickButton,
            self.ui.zoomButton,
        ):
            if X.isChecked():
                X.setAutoExclusive(False)
                X.setChecked(False)
                X.setAutoExclusive(True)

    def handleRubric(self, rubric):
        """Pass a rubric dict onward to the scene, if we have a scene.

        Args:
            rubric (dict): we don't care what's in it: that's for the scene
                and the rubric widget to agree on!

        Returns:
            None: Modifies self.scene
        """
        self.setToolMode("rubric")
        # TODO: move to "args"/"extra" kwarg of setToolMode when we add that
        if self.scene:  # TODO: not sure why, Issue #1283 workaround
            self.scene.changeTheRubric(rubric)

    def loadWindowSettings(self):
        """Loads the window settings."""
        # load the window geometry, else maximise.
        if self.parentMarkerUI.annotatorSettings["geometry"] is not None:
            self.restoreGeometry(self.parentMarkerUI.annotatorSettings["geometry"])
        else:
            self.showMaximized()

        # remember the "do not show again" checks
        if self.parentMarkerUI.annotatorSettings["markWarnings"] is not None:
            self.markWarn = self.parentMarkerUI.annotatorSettings["markWarnings"]
        if self.parentMarkerUI.annotatorSettings["rubricWarnings"] is not None:
            self.rubricWarn = self.parentMarkerUI.annotatorSettings["rubricWarnings"]

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
        """Saves current window settings and other state into the parent.

        Returns:
            None: modifies self.parentMarkerUI and self.scene
        """
        self.parentMarkerUI.annotatorSettings["geometry"] = self.saveGeometry()
        self.parentMarkerUI.annotatorSettings[
            "viewRectangle"
        ] = self.view.getCurrentViewRect()
        self.parentMarkerUI.annotatorSettings["markWarnings"] = self.markWarn
        self.parentMarkerUI.annotatorSettings["rubricWarnings"] = self.rubricWarn
        self.parentMarkerUI.annotatorSettings[
            "zoomState"
        ] = self.ui.zoomCB.currentIndex()
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
            msg = InfoMsg(
                self, "Please make an annotation, even if there is no answer."
            )
            msg.exec()
            return False

        # check annotations are inside the margins
        out_objs = self.scene.check_all_saveable_objects_inside()
        if out_objs:
            msg = f"{len(out_objs)} annotations are outside the margins."
            msg += " Please move or delete them before saving."
            info = "<p>Out-of-bounds objects are highlighted in orange.</p>"
            info += "<p><em>Note:</em> if you cannot see any such objects, "
            info += "you may be experiencing "
            info += '<a href="https://gitlab.com/plom/plom/-/issues/1792">Issue '
            info += "#1792</a>; please help us by copy-pasting the details below, "
            info += "along with any details about how to make this happen!</p>"
            details = "## Out of bounds objects\n\n  "
            details += "\n".join(str(x) for x in out_objs)
            details += "\n\n## All objects\n\n  "
            details += "\n".join(str(x) for x in self.scene.items())
            details += "\n\n## More detail on rect objects\n\n  "
            details += "Previous instances have involved QGraphicsRectItem so\n"
            details += "here are details about all those:\n\n"
            for x in self.scene.items():
                if isinstance(x, QGraphicsRectItem):
                    details += f"\n{x}"
                    details += f"\n  - {x.rect()}"
                    details += f"\n  - {x.pen()}"
                    c = x.pen().color()
                    details += "\n     - rgba: "
                    details += f"{(c.red(), c.green(), c.blue(), c.alpha())}"
                    details += f"\n     - width: {x.pen().width()}"
                    details += f"\n  - {x.brush()}"
                    details += f"\n     - style: {x.brush().style()}"
            details += "\n\n## Object serialization\n\n  "
            details += "\n".join(str(x) for x in self.scene.pickleSceneItems())
            WarnMsg(self, msg, info=info, info_pre=False, details=details).exec()
            return False

        if self.scene.is_neutral_state():
            msg = InfoMsg(self, "You have not yet set a score.")
            msg.exec()
            return False

        assert self.getScore() is not None

        # do some checks when score is zero
        if self.getScore() == 0:
            if not self._zeroMarksWarn():
                return False

        # do similar checks when score is full
        if self.getScore() == self.maxMark:
            if not self._fullMarksWarn():
                return False

        # warn if points where lost but insufficient annotations
        if (
            self.rubricWarn
            and (0 < self.getScore() < self.maxMark)
            and self.scene.hasOnlyTicksCrossesDeltas()
        ):
            msg = SimpleQuestionCheckBox(
                self,
                "<p>You have given neither comments nor detailed annotations "
                "(other than &#x2713; &#x2717; &plusmn;<i>n</i>).</p>\n"
                "<p>This may make it difficult for students to learn from this "
                "feedback.</p>\n"
                "<p>Are you sure you wish to continue?</p>",
                "Don't ask me again this session.",
            )
            if msg.exec() == QMessageBox.No:
                return False
            if msg.cb.isChecked():
                # Note: these are only saved if we ultimately accept
                self.rubricWarn = False

        # some combinations of rubrics may seem ambiguous or potentially confusing
        rubrics = self.scene.get_rubrics()
        ok, code, msg = check_for_illadvised(rubrics, self.maxMark)
        if not ok:
            # TODO: some more serious than others, may want to add
            # "don't ask me again" for only some.  For now, none.
            if SimpleQuestion(self, msg).exec() == QMessageBox.No:
                return False

        aname, plomfile = self.pickleIt()
        rubric_ids = self.scene.get_rubric_ids()

        log.debug("emitting accept signal")
        tim = self.timer.elapsed() // 1000

        # some things here hardcoded elsewhere too, and up in marker
        stuff = [
            self.getScore(),
            tim,
            self.paperDir,
            aname,
            plomfile,
            rubric_ids,
            self.integrity_check,
            self.src_img_data,
        ]
        self.annotator_upload.emit(self.tgvID, stuff)
        return True

    def _zeroMarksWarn(self):
        """
        A helper method for saveAnnotations.

        Controls warnings for when paper has 0 marks. If there are only-ticks or some-ticks then warns user.

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
                msg = SimpleQuestion(self, msg)
                if msg.exec() == QMessageBox.No:
                    return False
            elif self.markWarn:
                msg = SimpleQuestionCheckBox(
                    self, msg, "Don't ask me again this session."
                )
                if msg.exec() == QMessageBox.No:
                    return False
                if msg.cb.isChecked():
                    self.markWarn = False
        return True

    def _fullMarksWarn(self):
        """
        A helper method for saveAnnotations.

        Controls warnings for when paper has full marks. If there are some crosses or only crosses then warns user.

        Returns:
            False if user cancels, True otherwise.

        """
        msg = "<p>You have given full {0}/{0},".format(self.maxMark)
        warn = False
        forceWarn = False
        if self.scene.hasOnlyCrosses():
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
                msg = SimpleQuestion(self, msg)
                if msg.exec() == QMessageBox.No:
                    return False
            elif self.markWarn:
                msg = SimpleQuestionCheckBox(
                    self, msg, "Don't ask me again this session."
                )
                if msg.exec() == QMessageBox.No:
                    return False
                if msg.cb.isChecked():
                    self.markWarn = False

        return True

    def closeEvent(self, event):
        """
        Overrides QWidget.closeEvent().

        Deal with various cases of window trying to close.

        Notes: These include:

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

        log.debug("Clean up any lingering solution-views etc")
        if self.solutionView:
            log.debug("Cleaning a solution-view")
            self.solutionView.close()
            self.solutionView = None

        self.saveTabStateToServer(self.rubric_widget.get_tab_rubric_lists())

        # Save the current window settings for next time annotator is launched
        self.saveWindowSettings()

        # weird hacking to force close if we came from saving.
        # Appropriate signals have already been sent so just close
        force = getattr(self, "_priv_force_close", False)
        if force:
            log.debug("emitting the closing signal")
            self.annotator_done_closing.emit(self.tgvID)
            event.accept()
            return

        # We are here b/c of cancel button, titlebar close, or related
        if self.is_dirty():
            msg = SimpleQuestion(
                self,
                "<p>There are unsaved changes to the annotations.</p>\n"
                "<p>Do you want to discard changes and close the annotator?</p>",
            )
            if msg.exec() == QMessageBox.No:
                event.ignore()
                return

        log.debug("emitting reject/cancel signal, discarding, and closing")
        self.annotator_done_reject.emit(self.tgvID)
        event.accept()

    def is_dirty(self):
        """Is the scene dirty?

        Has the scene been annotated or changed this session? Re-opening
        a previous annotated scene does not dirty it, until changes are
        made. Changes could be made and then undone back to the clean state.
        The concept should be familiar to "file saved" in a text editor.
        """
        if not self.scene:
            return False
        return self.scene.is_dirty()

    def get_nonrubric_text_from_page(self):
        """Retrieves text (not in rubrics) from the scene.

        Returns:
            list: strings for text annotations not in a rubric.
        """
        if not self.scene:
            return []
        return self.scene.get_nonrubric_text_from_page()

    def latexAFragment(self, *args, **kwargs):
        """Latex a fragment of text."""
        return self.parentMarkerUI.latexAFragment(*args, **kwargs)

    def pickleIt(self):
        """Capture the annotated pages as a bitmap and a .plom file.

        1. Renders the current scene as a static bitmap.
        2. Retrieves current annotations in reverse chronological order.
        3. Adds various other metadata.
        4. Writes JSON into the ``.plom`` file.

        Note: called "pickle" for historical reasons: it is neither a
        Python pickle nor a real-life pickle.

        Return:
            tuple: two `pathlib.Path`, one for the rendered image and
            one for the ``.plom`` file.
        """
        aname = self.scene.save(self.saveName)
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        # get the crop-rect as proportions of underlying image
        # is 4-tuple (x,y,w,h) scaled by image width / height
        crop_rect_data = self.scene.current_crop_rectangle_as_proportions()
        # TODO: consider saving colour only if not red?
        # TODO: someday src_img_data may have other images not used
        plomData = {
            "base_images": self.src_img_data,
            "saveName": str(aname),
            "maxMark": self.maxMark,
            "currentMark": self.getScore(),
            "sceneScale": self.scene.get_scale_factor(),
            "annotationColor": self.scene.ink.color().getRgb()[:3],
            "crop_rectangle_data": crop_rect_data,
            "sceneItems": lst,
        }
        plomfile = self.saveName.with_suffix(".plom")
        with open(plomfile, "w") as fh:
            json.dump(plomData, fh, indent="  ")
            fh.write("\n")
        return aname, plomfile

    def unpickleIt(self, plomData):
        """
        Unpickles the page by calling scene.unpickleSceneItems and sets
        the page's mark.

        Args:
            plomData (dict): a dictionary containing the data for the
                                pickled .plom file.

        Returns:
            None

        """
        self.view.setHidden(True)
        if plomData.get("sceneScale", None):
            self.scene.set_scale_factor(plomData["sceneScale"])
        if plomData.get("annotationColor", None):
            self.scene.set_annotation_color(plomData["annotationColor"])
        # Put the scene items back
        self.scene.unpickleSceneItems(plomData["sceneItems"])
        # set crop rectangle from plom file contains if present
        # else, if use held-crop rectangle if present
        if plomData.get("crop_rectangle_data", None):
            self.scene.crop_from_plomfile(plomData["crop_rectangle_data"])
        else:
            if self.held_crop_rectangle_data:  # if a crop is being held, use it.
                self.scene.crop_from_plomfile(self.held_crop_rectangle_data)
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

    def getRubricsFromServer(self):
        """Request a latest rubric list for current question."""
        return self.parentMarkerUI.getRubricsFromServer(self.question_num)

    def saveTabStateToServer(self, tab_state):
        """Have Marker upload this tab state to the server."""
        self.parentMarkerUI.saveTabStateToServer(tab_state)

    def getTabStateFromServer(self):
        """Have Marker download the tab state from the server."""
        return self.parentMarkerUI.getTabStateFromServer()

    def refreshRubrics(self):
        """ask the rubric widget to refresh rubrics"""
        self.rubric_widget.refreshRubrics()

    def createNewRubric(self, new_rubric):
        """Ask server to create a new rubric with data supplied"""
        return self.parentMarkerUI.sendNewRubricToServer(new_rubric)

    def modifyRubric(self, key, updated_rubric):
        """Ask server to create a new rubric with data supplied"""
        return self.parentMarkerUI.modifyRubricOnServer(key, updated_rubric)

    def viewSolutions(self):
        solutionFile = self.parentMarkerUI.getSolutionImage()
        if solutionFile is None:
            InfoMsg(self, "No solution has been uploaded").exec()
            return

        if self.solutionView is None:
            self.solutionView = SolutionViewer(self, solutionFile)
        self.solutionView.show()

    def viewCat(self):
        CatViewer(self).exec()

    def viewNotCat(self):
        CatViewer(self, dogAttempt=True).exec()

    def tag_paper(self, task=None, dialog_parent=None):
        if not self.scene:
            return
        if not task:
            if not self.tgvID:
                return
            task = f"q{self.tgvID}"
        if not dialog_parent:
            dialog_parent = self
        self.parentMarkerUI.manage_task_tags(task, parent=dialog_parent)

    def refreshSolutionImage(self):
        log.debug("force a refresh")
        return self.parentMarkerUI.refreshSolutionImage()

    def show_previous(self):
        log.debug(
            f"Show previous called: debug history = {self.parentMarkerUI.marking_history}"
        )

        if not self.parentMarkerUI.marking_history:
            WarnMsg(
                self,
                "The client cannot determine the previous paper. Please cancel this annotation and select from the list.",
            ).exec()
            return
        keydata = self.get_key_bindings()
        PreviousPaperViewer(self, self.parentMarkerUI.marking_history, keydata).exec()

    def _get_annotation_by_task(self, task):
        return self.parentMarkerUI.get_file_for_previous_viewer(task)
