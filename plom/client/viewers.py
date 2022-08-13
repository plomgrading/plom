# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

import logging
from pathlib import Path
import random
import tempfile
import urllib.request

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QShortcut,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .image_view_widget import ImageViewWidget
from .useful_classes import InfoMsg, WarnMsg


log = logging.getLogger("viewerdialog")


class GroupView(QDialog):
    """Display one or more images with an Ok button.

    Args:
        parent (QWidget): the parent window of this dialog.
        fnames (list): a list of images, see ImageViewWidget docs.

    Keyword Args:
        title (None/str): optional title for dialog.
        bigger (bool): some weird hack to make a bigger-than-default
            dialog.  Using this is probably a sign you're doing
            something suboptimal.
        before_text (None/str): some text to display before the image
            at the top of the dialog.  Can include html formatting.
        after_text (None/str): some text to display after the image
            at the bottom of the dialog but above the buttons.
            Can include html formatting.
    """

    def __init__(
        self,
        parent,
        fnames,
        *,
        title=None,
        bigger=False,
        before_text=None,
        after_text=None,
    ):
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)
        self.testImg = ImageViewWidget(self, fnames, dark_background=True)
        grid = QVBoxLayout()
        if before_text:
            label = QLabel(before_text)
            label.setWordWrap(True)
            # label.setAlignment(Qt.AlignTop)
            grid.addWidget(label)
        grid.addWidget(self.testImg, 1)
        if after_text:
            label = QLabel(after_text)
            label.setWordWrap(True)
            grid.addWidget(label)
        # some extra space before the main dialog buttons
        grid.addSpacing(6)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        # keep a instance var in case a subclass wants to inject other buttons
        self._buttonBox = buttons
        grid.addWidget(buttons)
        self.setLayout(grid)
        if bigger:
            self.resize(
                QSize(
                    int(self.parent().width() * 2 / 3),
                    int(self.parent().height() * 11 / 12),
                )
            )
        if bigger:
            # TODO: seems needed for Ctrl-R double-click popup
            self.testImg.resetView()
            self.testImg.forceRedrawOrSomeBullshit()


class QuestionViewDialog(GroupView):
    """View the raw scans from a particular question, optionally with tagging.

    Args:
        parent: the parent of this dialog
        fnames (list): the files to use for viewing, `str` or `pathlib.Path`.
            We don't claim the files: caller should manage them and delete
            when done.
        testnum (int): which test/paper number is this
        questnum (int): which question number.  TODO: probably should
            support question label.
        ver (int/None): if we know the version, we can display it.
        marker (None/plom.client.Marker): used to talk to the server for
            tagging.
    """

    def __init__(self, parent, fnames, testnum, questnum, ver=None, marker=None):
        super().__init__(parent, fnames)
        s = f"Original ungraded images for test {testnum:04} question {questnum}"
        if ver:
            s += f" (ver {ver})"
        self.setWindowTitle(s)
        self.tgv = (testnum, questnum, ver)
        if marker:
            self.marker = marker
            tagButton = QPushButton("&Tags")
            tagButton.clicked.connect(self.tags)
            self._buttonBox.addButton(tagButton, QDialogButtonBox.ActionRole)

    def tags(self):
        """If we have a marker parent then use it to manage tags"""
        if self.marker:
            task = f"q{self.tgv[0]:04}g{self.tgv[1]}"
            self.marker.manage_task_tags(task, parent=self)


class WholeTestView(QDialog):
    def __init__(self, testnum, filenames, labels=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Original scans of test {testnum}")
        self.pageTabs = QTabWidget()
        closeButton = QPushButton("&Close")
        prevButton = QPushButton("&Previous")
        nextButton = QPushButton("&Next")
        grid = QVBoxLayout()
        grid.addWidget(self.pageTabs)
        buttons = QHBoxLayout()
        buttons.addWidget(prevButton, 1)
        buttons.addWidget(nextButton, 1)
        buttons.addSpacing(64)
        buttons.addStretch(2)
        buttons.addWidget(closeButton)
        grid.addLayout(buttons)
        self.setLayout(grid)
        prevButton.clicked.connect(self.previousTab)
        nextButton.clicked.connect(self.nextTab)
        closeButton.clicked.connect(self.accept)
        self.pageTabs.currentChanged.connect(self.tabSelected)
        self.setMinimumSize(500, 500)
        if not labels:
            labels = [f"{k + 1}" for k in range(len(filenames))]
        for f, label in zip(filenames, labels):
            # Tab doesn't seem to have padding so compact=False
            tab = ImageViewWidget(self, [f], compact=False)
            self.pageTabs.addTab(tab, label)

    def tabSelected(self, index):
        """Resize on change tab."""
        if index >= 0:
            self.pageTabs.currentWidget().resetView()

    def nextTab(self):
        t = self.pageTabs.currentIndex() + 1
        if t >= self.pageTabs.count():
            t = 0
        self.pageTabs.setCurrentIndex(t)

    def previousTab(self):
        t = self.pageTabs.currentIndex() - 1
        if t < 0:
            t = self.pageTabs.count() - 1
        self.pageTabs.setCurrentIndex(t)


class SelectTestQuestion(QDialog):
    def __init__(self, parent, info, gn=None):
        super().__init__(parent)
        self.setWindowTitle("View another test")
        self.iL = QLabel("From which test do you wish to view the current question?")
        self.ab = QPushButton("&Accept")
        self.ab.clicked.connect(self.accept)
        self.cb = QPushButton("&Cancel")
        self.cb.clicked.connect(self.reject)

        fg = QFormLayout()
        self.tsb = QSpinBox()
        self.tsb.setRange(1, info["numberToProduce"])
        self.tsb.setValue(1)
        fg.addRow("Select test:", self.tsb)
        if gn is not None:
            self.gsb = QSpinBox()
            self.gsb.setRange(1, info["numberOfQuestions"])
            self.gsb.setValue(gn)
            fg.addRow("Select question:", self.gsb)
            self.iL.setText("Which test/group do you wish to view?")
        grid = QGridLayout()
        grid.addWidget(self.iL, 0, 1, 1, 3)
        grid.addLayout(fg, 1, 1, 3, 3)
        grid.addWidget(self.ab, 4, 1)
        grid.addWidget(self.cb, 4, 3)
        self.setLayout(grid)


class SolutionViewer(QWidget):
    """A non-modal dialog for displaying solutions.

    A note on modality: because the super init call has no parent
    reference, this is a new top-level window (not formally parented
    by the Annotator or Marker windows).  At least in the Gnome
    environment, that means it does not stay on top of the Annotator
    window (unlike for example `QVHistogram` in Manager).
    """

    def __init__(self, parent, fname):
        super().__init__()
        self._annotr = parent
        grid = QVBoxLayout()
        self.sv = ImageViewWidget(self, fname)
        refreshButton = QPushButton("&Refresh")
        closeButton = QPushButton("&Close")
        maxNormButton = QPushButton("&Max/Norm")
        grid.addWidget(self.sv)
        buttons = QHBoxLayout()
        buttons.addWidget(refreshButton)
        buttons.addWidget(maxNormButton)
        buttons.addStretch(1)
        buttons.addWidget(closeButton)
        grid.addLayout(buttons)
        self.setLayout(grid)
        closeButton.clicked.connect(self.close)
        maxNormButton.clicked.connect(self.swapMaxNorm)
        refreshButton.clicked.connect(self.refresh)

        self.setWindowTitle(f"Solutions - {Path(fname).stem}")

        self.show()

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def refresh(self):
        solnfile = self._annotr.refreshSolutionImage()
        self.sv.updateImage(solnfile)
        if solnfile is None:
            WarnMsg(self, "Server no longer has a solution.  Try again later?").exec()


class CatViewer(QDialog):
    def __init__(self, parent, dogAttempt=False):

        self.msgs = [
            "PLOM",
            "I%20can%20haz%20more%20markingz",
            "Insert%20meme%20here",
            "Hello%20Omer",
            "More%20patz%20pleeze",
        ]

        super().__init__(parent)
        grid = QGridLayout()
        self.count = 0
        self.catz = None
        if dogAttempt:
            self.getNewImageFile(msg="No%20dogz.%20Only%20Catz%20and%20markingz")
        else:
            self.getNewImageFile()
        self.img = ImageViewWidget(self, self.catz)

        refreshButton = QPushButton("&Refresh")
        closeButton = QPushButton("&Close")
        grid.addWidget(self.img, 1, 1, 6, 7)
        grid.addWidget(refreshButton, 7, 1)
        grid.addWidget(closeButton, 7, 7)
        self.setLayout(grid)
        closeButton.clicked.connect(self.close)
        refreshButton.clicked.connect(self.refresh)

        self.setWindowTitle("Catz")

        self.setMinimumSize(500, 500)

    def closeEvent(self, event):
        self.eraseImageFile()

    def getNewImageFile(self, *, msg=None):
        """Erase the current stored image and try to get a new one.

        args:
            msg (None/str): something for the cat to say.

        returns:
            None: but sets the `.catz` instance variable as a side effect.
        """
        self.eraseImageFile()
        logging.debug("Trying to refresh cat image")

        # Do we need to manage this tempfile in instance variable? Issue #1842
        # with tempfile.NamedTemporaryFile() as f:
        #     urllib.request.urlretrieve("https://cataas.com/cat", f)
        #     self.img.updateImages(f)
        self.catz = Path(tempfile.NamedTemporaryFile(delete=False).name)

        try:
            if msg is None:
                urllib.request.urlretrieve("https://cataas.com/cat", self.catz)
            else:
                urllib.request.urlretrieve(
                    f"https://cataas.com/cat/says/{msg}", self.catz
                )
            logging.debug("Cat image refreshed")
        except Exception:
            WarnMsg(self, "Cannot get cat picture.  Try again later?").exec()
            self.catz = None

    def eraseImageFile(self):
        if self.catz is None:
            return
        try:
            self.catz.unlink()
        except OSError:
            pass

    def refresh(self):
        self.count += 1
        if self.count > 5:
            msg = "Back%20to%20work"
        elif random.choice([0, 1]):
            msg = random.choice(self.msgs)
        else:
            msg = None
        self.getNewImageFile(msg=msg)
        self.img.updateImage(self.catz)
        if self.count > 5:
            InfoMsg(self, "Enough break time").exec()
            self.close()


class PreviousPaperViewer(QDialog):
    """A modal dialog for displaying annotations of the previous paper."""

    def __init__(self, parent, task_history, keydata):
        super().__init__(parent)
        self._annotr = parent
        self.task_history = task_history
        self.index = len(task_history) - 1
        task = self.task_history[-1]

        fname = self._annotr._get_annotation_by_task(task)
        self.ivw = ImageViewWidget(self, fname)
        grid = QVBoxLayout()
        grid.addWidget(self.ivw)

        grid.addSpacing(6)
        buttons = QHBoxLayout()
        (key,) = keydata["quick-show-prev-paper"]["keys"]
        key = QKeySequence(key)
        keystr = key.toString(QKeySequence.NativeText)
        self.prevTaskB = QPushButton(f"&Previous ({keystr})")
        self.prevTaskB.clicked.connect(self.previous_task)
        self.prevShortCut = QShortcut(key, self)
        self.prevShortCut.activated.connect(self.previous_task)
        (key,) = keydata["quick-show-next-paper"]["keys"]
        key = QKeySequence(key)
        keystr = key.toString(QKeySequence.NativeText)
        self.nextTaskB = QPushButton(f"&Next ({keystr})")
        self.nextTaskB.clicked.connect(self.next_task)
        self.nextShortCut = QShortcut(key, self)
        self.nextShortCut.activated.connect(self.next_task)
        buttons.addWidget(self.prevTaskB, 1)
        buttons.addWidget(self.nextTaskB, 1)
        buttons.addSpacing(64)
        buttons.addStretch(2)
        tagButton = QPushButton("&Tag")
        tagButton.clicked.connect(self.tag_paper)
        buttons.addWidget(tagButton)
        b = QPushButton("&Close")
        b.clicked.connect(self.accept)
        buttons.addWidget(b)
        grid.addLayout(buttons)
        self.setLayout(grid)
        self.setWindowTitle(f"Previous annotations - {task}")

    def previous_task(self):
        self.nextTaskB.setEnabled(True)
        if self.index == 0:
            return
        self.index -= 1
        task = self.task_history[self.index]
        self.ivw.updateImage(self._annotr._get_annotation_by_task(task))
        self.setWindowTitle(f"Previous annotations - {task}")
        if self.index == 0:
            self.prevTaskB.setEnabled(False)

    def next_task(self):
        self.prevTaskB.setEnabled(True)
        if self.index == len(self.task_history) - 1:
            return
        self.index += 1
        task = self.task_history[self.index]
        self.ivw.updateImage(self._annotr._get_annotation_by_task(task))
        self.setWindowTitle(f"Previous annotations - {task}")
        if self.index == len(self.task_history) - 1:
            self.nextTaskB.setEnabled(False)

    def tag_paper(self):
        task = self.task_history[self.index]
        self._annotr.tag_paper(task=task, dialog_parent=self)
