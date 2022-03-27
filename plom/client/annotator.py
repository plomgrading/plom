# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022 Joey Shi

__copyright__ = "Copyright (C) 2018-2022 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Elvis Cai", "Colin Macdonald", "Victoria Schuster"]
__license__ = "AGPLv3"

from copy import deepcopy
import imghdr
import json
import logging
from pathlib import Path
import os
import re
import sys
import tempfile
from textwrap import dedent

if sys.version_info >= (3, 7):
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
    QAction,
    QActionGroup,
    QDialog,
    QWidget,
    QMenu,
    QMessageBox,
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
from .key_wrangler import KeyWrangler, key_layouts

# import the key-help popup window class
from .key_help import KeyHelp

from .origscanviewer import (
    RearrangementViewer,
    SolutionViewer,
    WholeTestView,
    CatViewer,
)
from .pagescene import PageScene
from .pageview import PageView
from .uiFiles.ui_annotator import Ui_annotator
from .useful_classes import ErrorMsg, WarnMsg
from .useful_classes import (
    ErrorMessage,
    SimpleQuestion,
    SimpleQuestionCheckBox,
    NoAnswerBox,
)


log = logging.getLogger("annotr")

# Short descriptions of each tool to display to user.
tipText = {
    "box": "Box: L = highlighted box, R/Shift = highlighted ellipse.",
    "rubric": "Rubric: L = paste rubric, R/Shift = labelled box",
    "rubric up": "Rubric up: Select previous rubric in list",
    "rubric down": "Rubric down: Select next rubric in list",
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

        # a solution view pop-up window - initially set to None
        self.solutionView = None

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
        self.maxMark = None

        # when rubrics are used, we just outline the rubric widget - not
        # the whole background - so make a style for that.
        self.currentButtonStyleOutline = "border: 2px solid #3daee9; "

        self.ui = Ui_annotator()

        # Set up the gui.
        self.ui.setupUi(self)

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

        self.ui.hamMenuButton.setMenu(self.buildHamburger())
        self.ui.hamMenuButton.setToolTip("Menu (F10)")
        self.ui.hamMenuButton.setPopupMode(QToolButton.InstantPopup)
        # no initial keybindings - get from the marker if non-default
        self.keyBindings = None
        self.setMiscShortCuts()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "Plom Client",
            dedent(
                f"""
                <p>Plom Client {__version__}</p>

                <p><a href="https://plomgrading.org">https://plomgrading.org</a></p>

                <p>Copyright &copy; 2018-2021 Andrew Rechnitzer,
                Colin B. Macdonald, and other contributors.</p>

                <p>Plom is Free Software, available under the GNU Affero
                General Public License version 3, or at your option, any
                later version.</p>
                """
            ),
        )

    def getScore(self):
        return self.scene.getScore()

    def getMarkingState(self):
        return self.scene.getMarkingState()

    def buildHamburger(self):
        # TODO: use QAction, share with other UI, shortcut keys written once
        m = QMenu()
        m.addAction("Next paper\tctrl-n", self.saveAndGetNext)
        m.addAction("Done (save and close)", self.saveAndClose)
        m.addAction("Defer and go to next", lambda: None).setEnabled(False)
        m.addAction("Previous paper", lambda: None).setEnabled(False)
        m.addAction("Close without saving\tctrl-c", self.close)
        m.addSeparator()
        m.addAction("View cat", self.viewCat)
        m.addAction("View dog", self.viewNotCat)
        m.addSeparator()
        m.addAction("View solutions\tF2", self.viewSolutions)
        m.addAction("Tag paper...\tF3", self.tag_paper)
        m.addSeparator()
        m.addAction("Adjust pages\tCtrl-r", self.rearrangePages)
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
            "Decrease annotation scale\tshift-[",
            lambda: self.change_annot_scale(1.0 / 1.1),
        )
        # Issue #1350: temporarily?
        m.addAction(
            "Temporarily change annot. colour",
            self.change_annotation_colour,
        )
        m.addSeparator()
        m.addAction("Synchronise rubrics", self.refreshRubrics)
        m.addAction("Compact UI\thome", self.narrowLayout)
        # TODO: this should be an indicator but for now compact doesn't have the hamburg menu
        # m.addAction("&Wide UI\thome", self.wideLayout)
        m.addSeparator()
        m.addAction("Help", lambda: None).setEnabled(False)
        m.addAction("Show shortcut keys...\t?", self.keyPopUp)
        # key-binding submenu stuff
        km = m.addMenu("Set major keys")
        # to make these actions checkable, they need to belong to self.
        kmg = QActionGroup(m)
        for name in key_layouts:
            setattr(self, "kb_{}_act".format(name), QAction("Use {} keys".format(name)))
            getattr(self, "kb_{}_act".format(name)).setCheckable(True)
            km.addAction(getattr(self, "kb_{}_act".format(name)))
            kmg.addAction(getattr(self, "kb_{}_act".format(name)))
        # TODO - get this inside the loop with correct lambda function scope hackery
        self.kb_sdf_act.triggered.connect(lambda: self.setKeyBindingsToDefault("sdf"))
        self.kb_sdf_french_act.triggered.connect(
            lambda: self.setKeyBindingsToDefault("sdf_french")
        )
        self.kb_dvorak_act.triggered.connect(
            lambda: self.setKeyBindingsToDefault("sdf_dvorak")
        )
        self.kb_asd_act.triggered.connect(lambda: self.setKeyBindingsToDefault("asd"))
        self.kb_jkl_act.triggered.connect(lambda: self.setKeyBindingsToDefault("jkl"))

        km.addSeparator()
        self.kb_custom_act = QAction("Use custom keys")
        self.kb_custom_act.setCheckable(True)
        self.kb_custom_act.triggered.connect(self.setKeyBindings)
        kmg.addAction(self.kb_custom_act)
        km.addAction(self.kb_custom_act)
        m.addAction("About Plom", self.show_about_dialog)
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
        if self.scene.mode == "rubric":  # stores as [a,b]
            # if no rubric selected then key=None - be careful of this.
            self.modeInformation.append(self.rubric_widget.getCurrentRubricKeyAndTab())

        # after grabbed mode information, reset rubric_widget
        self.rubric_widget.reset()
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
            question_label (str): The name of the question we are
                marking.  This is generally used for display only as
                there is an integer for precise usage.
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
        self.rubric_widget.changeMark(
            self.getScore(), self.getMarkingState(), self.maxMark
        )
        self.rubric_widget.setQuestionNumber(self.question_num)
        self.rubric_widget.setEnabled(True)

        # TODO: Make handling of rubric less hack.
        log.debug("Restore mode info = {}".format(self.modeInformation))
        self.scene.setToolMode(self.modeInformation[0])
        if self.modeInformation[0] == "rubric":
            # self.modeInformation[1] = [a,b] = [key, tab-index]
            if self.rubric_widget.setCurrentRubricKeyAndTab(
                self.modeInformation[1][0], self.modeInformation[1][1]
            ):
                self.rubric_widget.handleClick()
            else:  # if that rubric-mode-set fails (eg - no such rubric)
                self.scene.setToolMode("move")
        # redo this after all the other rubric stuff initialised
        self.rubric_widget.changeMark(
            self.getScore(), self.getMarkingState(), self.maxMark
        )

        # Very last thing = unpickle scene from plomDict
        if plomDict is not None:
            self.unpickleIt(plomDict)

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
            self.ui.markLabel.setText("No mark")
            self.ui.narrowMarkLabel.setText("No mark")
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
            pm.loadFromData(resources.read_binary(plom.client.cursors, f))
            return pm

        self.cursorBox = QCursor(_pixmap_from("box.png"), 4, 4)
        self.cursorEllipse = QCursor(_pixmap_from("ellipse.png"), 4, 4)
        self.cursorCross = QCursor(_pixmap_from("cross.png"), 4, 4)
        self.cursorDelete = QCursor(_pixmap_from("delete.png"), 4, 4)
        self.cursorLine = QCursor(_pixmap_from("line.png"), 4, 4)
        self.cursorPen = QCursor(_pixmap_from("pen.png"), 4, 4)
        self.cursorTick = QCursor(_pixmap_from("tick.png"), 4, 4)
        self.cursorQMark = QCursor(_pixmap_from("question_mark.png"), 4, 4)
        self.cursorHighlight = QCursor(_pixmap_from("highlighter.png"), 4, 4)
        self.cursorArrow = QCursor(_pixmap_from("arrow.png"), 4, 4)
        self.cursorDoubleArrow = QCursor(_pixmap_from("double_arrow.png"), 4, 4)

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
        # list of minor modes in order
        L = ["box", "tick", "cross", "text", "line", "pen"]

        if not hasattr(self, "_which_tool"):
            self._which_tool = "box"

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

        TODO: this has significant duplication with RearrangePages.  Currently
        this one does it own downloads (even though Marker may already have the
        pages.

        Returns:
            None
        """
        if not self.tgvID:
            return
        testnum = self.tgvID[:4]
        log.debug("wholePage: downloading files for testnum %s", testnum)
        page_data, files = self.parentMarkerUI.downloadWholePaper(testnum)
        if not files:
            return
        labels = [x[0] for x in page_data]
        WholeTestView(testnum, files, labels, parent=self).exec_()
        for f in files:
            f.unlink()

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
        # TODO: maybe download should happen in Marker?
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
            ErrorMessage(
                "Warning: duplicate pages detected!",
                info=info,
                info_pre=False,
                details=f"Annotator's image_md5_list is\n  {image_md5_list}\n"
                f"The src_img_data is\n  {self.src_img_data}\n"
                f"Include this info if you think this is a bug!",
            ).exec_()
        log.debug("adjustpgs: downloading files for testnum {}".format(testNumber))
        # do a deep copy of this list of dict - else hit #1690
        # keep original readonly?
        page_data = deepcopy(self.parentMarkerUI._full_pagedata[int(testNumber)])
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
                ErrorMessage(s).exec_()
        # Crawl over the page_data, download any images we don't have
        # TODO: could defer downloading to background thread of dialog
        page_adjuster_downloads = []
        for (i, pg) in enumerate(page_data):
            if pg["local_filename"]:
                log.info(
                    "adjustpgs: already have image id={}: {}".format(
                        pg["id"], pg["local_filename"]
                    )
                )
                continue
            md5 = pg["md5"]
            image_id = pg["id"]
            img_bytes = self.parentMarkerUI.downloadOneImage(image_id, md5)
            img_ext = imghdr.what(None, h=img_bytes)
            # TODO: wrong to put these in the paperdir (?)
            # Maybe Marker should be doing this downloading
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=self.parentMarkerUI.workingDirectory,
                prefix="adj_pg_{}_".format(i),
                suffix=f".{img_ext}",
                delete=False,
            ) as f:
                log.info(
                    'adjustpages: write "%s" from id=%s, md5=%s', f.name, image_id, md5
                )
                f.write(img_bytes)
                page_adjuster_downloads.append(f.name)
                pg["local_filename"] = f.name

        is_dirty = self.scene.areThereAnnotations()
        log.debug("page_data is\n  {}".format("\n  ".join([str(x) for x in page_data])))
        # pull stuff out of dict (TODO: for now)
        page_data_list = []
        for d in page_data:
            page_data_list.append(
                [
                    d["pagename"],
                    d["md5"],
                    d["included"],
                    d["order"],
                    d["id"],
                    d["local_filename"],
                ]
            )
        rearrangeView = RearrangementViewer(
            self, testNumber, self.src_img_data, page_data_list, is_dirty
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
            # Sanity check for dupes in the permutation
            # pylint: disable=unsubscriptable-object
            md5 = [x[0] for x in perm]
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
                ErrorMessage(s).exec_()
            oldtgv = self.tgvID
            self.closeCurrentTGV()
            stuff = self.parentMarkerUI.PermuteAndGetSamePaper(oldtgv, perm)
            log.debug("permuted: new stuff is {}".format(stuff))
            if not stuff:
                txt = """
                    <p>Marker did not give us back the permuted material for
                    marking.</p>
                    <p>Probably you cancelled a download that we shouldn't be waiting
                    on anyway&mdash;see
                    <a href="https://gitlab.com/plom/plom/-/issues/1967">Issue #1967</a>.
                    </p>
                """
                ErrorMsg(self, txt).exec_()
            self.loadNewTGV(*stuff)
        # CAREFUL, wipe only those files we created
        # TODO: consider a broader local caching system
        for f in page_adjuster_downloads:
            os.unlink(f)
        self.setEnabled(True)
        return

    def experimental_cycle(self):
        self.scene.whichLineToDraw_next()

    def keyPopUp(self):
        """Sets KeyPress shortcuts."""
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

    def setToolMode(self, newMode, newCursor, imagePath=None):
        """
        Changes the current tool mode and cursor.

        Notes:
            TODO: this does various other mucking around for legacy
            reasons: could probably still use some refactoring.

        Returns:
            None: Modifies self
        """
        # We have to be a little careful since not all widgets get the styling in the same way.
        # If the mark-handler widget sent us here, it takes care of its own styling - so we update the little tool-tip

        if self.sender() in self.ui.frameTools.children():
            # tool buttons change the mode
            self.sender().setChecked(True)
        else:
            pass

        if imagePath is not None:
            self.scene.tempImagePath = imagePath

        # pass the new mode to the graphicsview, and set the cursor in view
        if self.scene:
            self.scene.setToolMode(newMode)
            self.view.setCursor(newCursor)
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
        pm.loadFromData(resources.read_binary(plom.client.icons, iconfile))
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
            oldtgv = self.tgvID
            self.closeCurrentTGV()
        else:
            oldtgv = None

        # Workaround getting too far ahead of Marker's upload queue
        queue_len = self.parentMarkerUI.get_upload_queue_length()
        if queue_len >= 3:
            ErrorMessage(
                f"<p>Plom is waiting to upload {queue_len} papers.</p>"
                + "<p>This might indicate network trouble: unfortunately Plom "
                + "does not yet deal with this gracefully and there is a risk "
                + "we might lose your non-uploaded work!</p>"
                + "<p>You should consider closing the Annotator, and waiting "
                + "a moment to see if the queue of &ldquo;uploading...&rdquo; "
                + "papers clear.</p>"
            ).exec_()

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

    def changeMainShortCuts(self, keys):
        # basic tool keys
        self.keyBindings = keys
        # save to parent-marker
        self.parentMarkerUI.annotatorSettings["tool_keys"] = keys
        # shortcuts already in place - just need to update the keys
        mainShortCuts = [
            ("undo", "toUndo"),
            ("redo", "toRedo"),
            ("nextRubric", "rubricMode"),
            ("previousRubric", "prev_rubric"),
            ("nextTab", "next_tab"),
            ("previousTab", "prev_tab"),
            ("nextTool", "next_minor_tool"),
            ("previousTool", "prev_minor_tool"),
            ("delete", "toDeleteMode"),
            ("move", "toMoveMode"),
            ("zoom", "toZoomMode"),
        ]
        for (name, command) in mainShortCuts:
            # self.nameSC.setKey(keys[name])
            getattr(self, name + "SC").setKey(keys[name])

    def setKeyBindings(self):
        kw = KeyWrangler(self, self.keyBindings)
        if kw.exec_() == QDialog.Accepted:
            self.changeMainShortCuts(kw.getKeyBindings())

    def setKeyBindingsToDefault(self, name):
        if name not in key_layouts:
            return
        else:
            self.changeMainShortCuts(key_layouts[name])

    def setMainShortCuts(self):
        # basic tool keys
        if self.keyBindings is None:
            self.keyBindings = key_layouts["sdf"]
            # set the menu action item
            self.kb_sdf_act.setChecked(True)

        # use sdf defaults unless saved
        if self.parentMarkerUI.annotatorSettings["tool_keys"] is None:
            keys = self.keyBindings
        else:
            # check all required present
            if all(
                act in self.parentMarkerUI.annotatorSettings["tool_keys"]
                for act in key_layouts["sdf"]
            ):
                keys = self.parentMarkerUI.annotatorSettings["tool_keys"]
                # TODO - this just clicks "custom" - might be better to detect if known binding.
                self.kb_custom_act.setChecked(True)
            else:  # not all there so use sdf-defaults
                keys = self.keyBindings

        mainShortCuts = [
            ("undo", "toUndo"),
            ("redo", "toRedo"),
            ("nextRubric", "rubricMode"),
            ("previousRubric", "prev_rubric"),
            ("nextTab", "next_tab"),
            ("previousTab", "prev_tab"),
            ("nextTool", "next_minor_tool"),
            ("previousTool", "prev_minor_tool"),
            ("delete", "toDeleteMode"),
            ("move", "toMoveMode"),
            ("zoom", "toZoomMode"),
        ]
        for (name, command) in mainShortCuts:
            # self.nameSC = QShortCut(QKeySequence(keys[name]), self)
            setattr(self, name + "SC", QShortcut(QKeySequence(keys[name]), self))
            # self.nameSC.activated.connect(self.command)
            getattr(self, name + "SC").activated.connect(getattr(self, command))

    def setMinorShortCuts(self):
        minorShortCuts = [
            ("swapMaxNorm", Qt.Key_Backslash, self.swapMaxNorm),
            ("zoomIn", "+", self.view.zoomIn),
            ("zoomIn2", "=", self.view.zoomIn),
            ("zoomOut", "-", self.view.zoomOut),
            ("zoomOut2", "_", self.view.zoomOut),
            ("keyHelp", "?", self.keyPopUp),
            ("toggle", Qt.Key_Home, self.toggleTools),
            ("viewWhole", Qt.Key_F1, self.viewWholePaper),
            ("viewSolutions", Qt.Key_F2, self.viewSolutions),
            ("tag_paper", Qt.Key_F3, self.tag_paper),
            ("hamburger", Qt.Key_F10, self.ui.hamMenuButton.animateClick),
        ]
        for (name, key, command) in minorShortCuts:
            # self.nameSC = QShortCut(QKeySequence(key), self)
            setattr(self, name + "SC", QShortcut(QKeySequence(key), self))
            # self.nameSC.activated.connect(command)
            getattr(self, name + "SC").activated.connect(command)
        # rubric shortcuts
        for n in range(1, 11):
            setattr(
                self,
                "rubricChange{}SC".format(n),
                QShortcut(QKeySequence("{}".format(n % 10)), self),
            )
        # unfortunately couldn't quite get the set command as lambda-function working in the loop
        self.rubricChange1SC.activated.connect(lambda: self.keyToChangeRubric(1))
        self.rubricChange2SC.activated.connect(lambda: self.keyToChangeRubric(2))
        self.rubricChange3SC.activated.connect(lambda: self.keyToChangeRubric(3))
        self.rubricChange4SC.activated.connect(lambda: self.keyToChangeRubric(4))
        self.rubricChange5SC.activated.connect(lambda: self.keyToChangeRubric(5))
        self.rubricChange6SC.activated.connect(lambda: self.keyToChangeRubric(6))
        self.rubricChange7SC.activated.connect(lambda: self.keyToChangeRubric(7))
        self.rubricChange8SC.activated.connect(lambda: self.keyToChangeRubric(8))
        self.rubricChange9SC.activated.connect(lambda: self.keyToChangeRubric(9))
        self.rubricChange10SC.activated.connect(lambda: self.keyToChangeRubric(10))
        # not so elegant - but it works

    def setMiscShortCuts(self):
        """
        Sets miscellaneous shortcuts.

        Returns:
            None: adds shortcuts.

        """
        # set main and minor shortcuts
        self.setMainShortCuts()
        self.setMinorShortCuts()

        # Now other misc shortcuts
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
        # TODO: this is one of our left/right keybindings
        self.redoShortCut2 = QShortcut(QKeySequence("Shift+g"), self)
        self.redoShortCut2.activated.connect(self.ui.redoButton.animateClick)

        self.twisterShortCut = QShortcut(QKeySequence("Ctrl+r"), self)
        self.twisterShortCut.activated.connect(self.rearrangePages)

        self.sekritShortCut = QShortcut(QKeySequence("Ctrl+Shift+o"), self)
        self.sekritShortCut.activated.connect(self.experimental_cycle)

        # pan shortcuts
        self.panShortCut = QShortcut(QKeySequence("space"), self)
        self.panShortCut.activated.connect(self.view.panThrough)
        self.depanShortCut = QShortcut(QKeySequence("Shift+space"), self)
        self.depanShortCut.activated.connect(self.view.depanThrough)
        self.slowPanShortCut = QShortcut(QKeySequence("Ctrl+space"), self)
        self.slowPanShortCut.activated.connect(lambda: self.view.panThrough(0.02))
        self.slowDepanShortCut = QShortcut(QKeySequence("Ctrl+Shift+space"), self)
        self.slowDepanShortCut.activated.connect(lambda: self.view.depanThrough(0.02))

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

    # Simple mode change functions
    def boxMode(self):
        """Changes the tool to box."""
        self.setToolMode("box", self.cursorBox)

    def rubricMode(self):
        """Changes the tool to rubric."""
        if not self.scene:
            self.rubric_widget.nextRubric()
            return
        if self.scene.mode == "rubric":
            self.rubric_widget.nextRubric()
        else:
            self.rubric_widget.reselectCurrentRubric()

    def crossMode(self):
        """Changes the tool to crossMode."""
        self.setToolMode("cross", self.cursorCross)

    def toDeleteMode(self):
        self.ui.deleteButton.animateClick()

    def deleteMode(self):
        """Changes the tool to delete."""
        self.setToolMode("delete", self.cursorDelete)

    def lineMode(self):
        """Changes the tool to the line button."""
        self.setToolMode("line", self.cursorLine)

    def toMoveMode(self):
        self.ui.moveButton.animateClick()

    def moveMode(self):
        """Changes the tool to the move button."""
        self.setToolMode("move", Qt.OpenHandCursor)

    def panMode(self):
        """Changes the tool to the pan button."""
        self.setToolMode("pan", Qt.OpenHandCursor)
        # The pan button also needs to change dragmode in the view
        self.view.setDragMode(1)

    def penMode(self):
        """Changes the tool to the pen button."""
        self.setToolMode("pen", self.cursorPen)

    def textMode(self):
        """Changes the tool to the text button."""
        self.setToolMode("text", Qt.IBeamCursor)

    def tickMode(self):
        """Changes the tool to the tick button."""
        self.setToolMode("tick", self.cursorTick)

    def toZoomMode(self):
        self.ui.zoomButton.animateClick()

    def zoomMode(self):
        """Changes the tool to the zoom button."""
        self.setToolMode("zoom", Qt.SizeFDiagCursor)

    def loadModeFromBefore(self, mode, aux=None):
        """
        Loads mode from previous.

        Args:
            mode (str): String corresponding to the toolMode to be loaded
            aux (int) : the row of the current rubric if applicable.

        Returns:
            None
        """
        self.loadModes = {
            "box": lambda: self.ui.boxButton.animateClick(),
            "rubric": lambda: self.rubricMode(),
            "cross": lambda: self.ui.crossButton.animateClick(),
            "line": lambda: self.ui.lineButton.animateClick(),
            "pen": lambda: self.ui.penButton.animateClick(),
            "text": lambda: self.ui.textButton.animateClick(),
            "tick": lambda: self.ui.tickButton.animateClick(),
        }
        if mode == "rubric" and aux is not None:  # key and tab set as [a,b]
            self.rubric_widget.setCurrentRubricKeyAndTab(aux[0], aux[1])
            # simulate a click on the rubric to get everything set.
            self.rubric_widget.handleClick()
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
            self.setToolMode("image", Qt.ClosedHandCursor, fileName)

    def setButtons(self):
        """Connects buttons to their corresponding functions."""
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
        self.ui.undoButton.clicked.connect(self.undo)
        self.ui.redoButton.clicked.connect(self.redo)

        # Connect the rubric buttons to the rubric list
        # They select the item and trigger its handleClick which fires
        # off a rubricSignal which will be picked up by the annotator
        # First up connect the rubric list's signal to the annotator's
        # handle rubric function.
        self.rubric_widget.rubricSignal.connect(self.handleRubric)
        # the no-answer button
        self.ui.noAnswerButton.clicked.connect(self.noAnswer)
        # and the rearrange pages button
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

    def handleRubric(self, dlt_txt):
        """Pass rubric ID, delta, and text the scene.

        Args:
            dlt_txt (tuple): the delta, string of text, rubric_id, and
                kind, e.g., `[-2, "missing chain rule", 12345, "relative"]`

        Returns:
            None: Modifies self.scene and self.toolMode
        """
        # Set the model to text and change cursor.
        self.setToolMode("rubric", QCursor(Qt.IBeamCursor))
        if self.scene:  # TODO: not sure why, Issue #1283 workaround
            self.scene.changeTheRubric(
                dlt_txt[0], dlt_txt[1], dlt_txt[2], dlt_txt[3], annotatorUpdate=True
            )

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

        # remember the last tool used
        if self.parentMarkerUI.annotatorSettings["tool"] is not None:
            if self.parentMarkerUI.annotatorSettings["tool"] == "rubric":
                rbrc = self.parentMarkerUI.annotatorSettings["rubric"]
                self.loadModeFromBefore("rubric", rbrc)
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
        self.parentMarkerUI.annotatorSettings["tool"] = self.scene.mode
        if self.scene.mode == "rubric":
            self.parentMarkerUI.annotatorSettings[
                "rubric"
            ] = self.rubric_widget.getCurrentRubricKeyAndTab()

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
        out_objs = self.scene.checkAllObjectsInside()
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
            WarnMsg(self, msg, info=info, info_pre=False, details=details).exec_()
            return False

        # make sure not still in "neutral" marking-state = no score given
        if self.getMarkingState() == "neutral":
            msg = ErrorMessage("You have not yet set a score.")
            msg.exec_()
            return False

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
            if msg.exec_() == QMessageBox.No:
                return False
            if msg.cb.checkState() == Qt.Checked:
                # Note: these are only saved if we ultimately accept
                self.rubricWarn = False

        aname, plomfile = self.pickleIt()
        rubrics = self.scene.get_rubrics_from_page()

        # Save the current window settings for next time annotator is launched
        self.saveWindowSettings()

        log.debug("emitting accept signal")
        tim = self.timer.elapsed() // 1000

        # some things here hardcoded elsewhere too, and up in marker
        stuff = [
            self.getScore(),
            tim,
            self.paperDir,
            aname,
            plomfile,
            rubrics,
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
                if msg.exec_() == QMessageBox.No:
                    return False
            elif self.markWarn:
                msg = SimpleQuestionCheckBox(
                    self, msg, "Don't ask me again this session."
                )
                if msg.exec_() == QMessageBox.No:
                    return False
                if msg.cb.checkState() == Qt.Checked:
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
                if msg.exec_() == QMessageBox.No:
                    return False
            elif self.markWarn:
                msg = SimpleQuestionCheckBox(
                    self, msg, "Don't ask me again this session."
                )
                if msg.exec_() == QMessageBox.No:
                    return False
                if msg.cb.checkState() == Qt.Checked:
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
            msg = SimpleQuestion(
                self,
                "<p>There are annotations on the page.</p>\n"
                "<p>Do you want to discard them and close the annotator?</p>",
            )
            if msg.exec_() == QMessageBox.No:
                event.ignore()
                return

        log.debug("emitting reject/cancel signal, discarding, and closing")
        self.annotator_done_reject.emit(self.tgvID)
        event.accept()

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
        3. Adds varous other metadata.
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
        # TODO: consider saving colour only if not red?
        # TODO: someday src_img_data may have other images not used
        plomData = {
            "base_images": self.src_img_data,
            "saveName": str(aname),
            "markState": self.getMarkingState(),
            "maxMark": self.maxMark,
            "currentMark": self.getScore(),
            "sceneScale": self.scene.get_scale_factor(),
            "annotationColor": self.scene.ink.color().getRgb()[:3],
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
        self.scene.unpickleSceneItems(plomData["sceneItems"])
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
        # ID for no-answer rubric is defined in the db_create module
        # in the createNoAnswerRubric function.
        # rID = 1000 + questionNumber = is absolute rubric

        noAnswerCID = 1000 + self.question_num

        # can only apply this if current marking state is neutral
        # else user has scored the page

        if self.getMarkingState() != "neutral":
            ErrorMessage(
                'You have marked the page - cannot then set "No answer given". Delete mark-changes before trying again.'
            ).exec_()
            return

        self.scene.noAnswer(noAnswerCID)
        nabValue = NoAnswerBox(self).exec_()
        if nabValue == 0:
            # equivalent to cancel - apply undo three times (to remove the noanswer lines+rubric)
            self.scene.undo()
            self.scene.undo()
            self.scene.undo()
        elif nabValue == 1:
            # equivalent to "yes - give me next paper"
            self.ui.finishedButton.animateClick()
        else:
            pass

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
            ErrorMessage("No solution has been uploaded").exec_()
            return

        if self.solutionView is None:
            self.solutionView = SolutionViewer(self, solutionFile)
        self.solutionView.show()

    def viewCat(self):
        CatViewer(self).exec()

    def viewNotCat(self):
        CatViewer(self, dogAttempt=True).exec()

    def tag_paper(self):
        task = f"q{self.tgvID}"
        self.parentMarkerUI.manage_task_tags(task, parent=self)

    def refreshSolutionImage(self):
        log.debug("force a refresh")
        return self.parentMarkerUI.refreshSolutionImage()
