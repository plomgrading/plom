# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .image_view_widget import ImageViewWidget
from .useful_classes import WarnMsg


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
            # label.setAlignment(Qt.AlignmentFlag.AlignTop)
            grid.addWidget(label)
        grid.addWidget(self.testImg, 1)
        if after_text:
            label = QLabel(after_text)
            label.setWordWrap(True)
            grid.addWidget(label)
        # some extra space before the main dialog buttons
        grid.addSpacing(6)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
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
    """View the pages for a particular question, optionally with tagging.

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

    def __init__(self, parent, fnames, papernum, q, marker=None, title=None):
        super().__init__(parent, fnames)
        self.papernum = papernum
        self.question_index = q
        if title:
            self.setWindowTitle(title)
        if marker:
            self.marker = marker
            tagButton = QPushButton("&Tags")
            tagButton.clicked.connect(self.tags)
            self._buttonBox.addButton(tagButton, QDialogButtonBox.ButtonRole.ActionRole)

    def tags(self):
        """If we have a marker parent then use it to manage tags."""
        if self.marker:
            task = f"q{self.papernum:04}g{self.question_index}"
            self.marker.manage_task_tags(task, parent=self)


class WholeTestView(QDialog):
    """View all the pages of a particular test."""

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
        """Change to the next tab."""
        t = self.pageTabs.currentIndex() + 1
        if t >= self.pageTabs.count():
            t = 0
        self.pageTabs.setCurrentIndex(t)

    def previousTab(self):
        """Change to the previous tab."""
        t = self.pageTabs.currentIndex() - 1
        if t < 0:
            t = self.pageTabs.count() - 1
        self.pageTabs.setCurrentIndex(t)


class SelectPaperQuestion(QDialog):
    """Select paper and question number.

    Args:
        parent: the parent of this dialog.
        qlabels: the questions labels.

    Keyword Args:
        initial_idx: which question (index) is initially selected.
            Indexed from one.
        min_papernum: limit the paper number selection to at least this
            value.  Defaults to 0.
        max_papernum: limit the paper number selection to at most this
            value.  If ``None`` then no maximum is specified.
    """

    def __init__(
        self,
        parent: QWidget,
        qlabels: list[str],
        *,
        initial_idx: int | None = None,
        min_papernum: int = 0,
        max_papernum: int | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("View another paper")
        flay = QFormLayout()
        self.tsb = QSpinBox()
        self.tsb.setMinimum(min_papernum)
        if max_papernum is not None:
            self.tsb.setMaximum(max_papernum)
        self.tsb.setValue(1)
        flay.addRow("Select paper:", self.tsb)
        q = QComboBox()
        q.addItems(qlabels)
        if initial_idx is not None:
            q.setCurrentIndex(initial_idx - 1)
        flay.addRow("Select question:", q)
        self.which_question = q
        self.annotations = QCheckBox("Show annotations")
        self.annotations.setChecked(True)
        flay.addWidget(self.annotations)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vlay = QVBoxLayout()
        vlay.addWidget(QLabel("Which paper and question do you wish to view?"))
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

    def get_results(self) -> tuple[int, int, bool]:
        """Return a tuple of what the user has set in the dialog."""
        return (
            self.tsb.value(),
            self.which_question.currentIndex() + 1,
            self.annotations.isChecked(),
        )


class SolutionViewer(QWidget):
    """A non-modal dialog for displaying solutions.

    A note on modality: because the super init call has no parent
    reference, this is a new top-level window (not formally parented
    by the Annotator or Marker windows).  At least in the Gnome
    environment, that means it does not stay on top of the Annotator
    window (unlike for example `QVHistogram` in Manager).

    The parent must be an Annotator, or otherwise have a method
    ``refreshSolutionImage`` that behaves like Annotator.
    """

    def __init__(self, parent: QWidget, fname: Path) -> None:
        super().__init__()
        self._annotr = parent
        grid = QVBoxLayout()
        self.sv = ImageViewWidget(self, fname)
        refreshButton = QPushButton("&Refresh")
        closeButton = QPushButton("&Close")
        grid.addWidget(self.sv)
        buttons = QHBoxLayout()
        buttons.addWidget(refreshButton)
        buttons.addStretch(1)
        buttons.addWidget(closeButton)
        grid.addLayout(buttons)
        self.setLayout(grid)
        closeButton.clicked.connect(self.close)
        refreshButton.clicked.connect(self.refresh)

        self.setWindowTitle(f"Solutions - {fname.stem}")

        self.show()

    def refresh(self):
        """Re-download the solution image from the server."""
        fname = self._annotr.refreshSolutionImage()
        self.sv.updateImage(fname)
        if fname is None:
            WarnMsg(self, "Server no longer has a solution.  Try again later?").exec()
        self.setWindowTitle(f"Solutions - {fname.stem}")


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
        keystr = key.toString(QKeySequence.SequenceFormat.NativeText)
        self.prevTaskB = QPushButton(f"&Previous ({keystr})")
        self.prevTaskB.clicked.connect(self.previous_task)
        self.prevShortCut = QShortcut(key, self)
        self.prevShortCut.activated.connect(self.previous_task)
        (key,) = keydata["quick-show-next-paper"]["keys"]
        key = QKeySequence(key)
        keystr = key.toString(QKeySequence.SequenceFormat.NativeText)
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
        """Move to the previous task in the list of task history."""
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
        """Move to the next task in the list of task history."""
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
        """Tag the paper on the server by asking the parent Annotator to do it."""
        task = self.task_history[self.index]
        self._annotr.tag_paper(task=task, dialog_parent=self)
