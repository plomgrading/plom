# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from plom.client import ImageViewWidget
from plom.client.useful_classes import WarningQuestion


review_beta_warning = """
    <p><b>Caution:</b> reviewing is a <em>beta</em> feature;
    it is not well-tested.  Use this at your own risk!</p>
    <p>If you flag this work for review, you'll then need to login
    with the Client using a special "reviewer" account.</p>
"""

revert_beta_warning = """
    <p><b>Caution:</b> reverting is a <em>beta</em> feature;
    it is not well-tested.  Use this at your own risk!</p>
    <p>You cannot undo reversion of tasks.</p>
"""


class ReviewViewWindow(QDialog):
    """View annotated image and provide access to parent's features for tagging and flagging for review.

    Note: parent will need to have two specific functions for the action
    buttons to work: see code.
    """

    def __init__(self, parent, fnames, *, stuff=None):
        super().__init__(parent)
        img = ImageViewWidget(self, fnames, dark_background=True)

        self.papernum, self.question, question_label, self.who = stuff
        self.setWindowTitle(f"Paper {self.papernum:04} {question_label}")
        explanation = QLabel(
            f"""
            <p>Paper {self.papernum:04} {question_label}.
            Graded by: {self.who}</p>
            """
        )
        explanation.setWordWrap(True)

        grid = QVBoxLayout()
        grid.addWidget(img, 1)
        grid.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        # connect the okay-button to 'accept'
        buttons.accepted.connect(self.accept)
        # construct and connect other buttons
        b = QPushButton("Flag for &review")
        b.clicked.connect(self.flag)
        buttons.addButton(b, QDialogButtonBox.ButtonRole.ActionRole)
        b = QPushButton("&Tags...")
        b.clicked.connect(self.tags)
        buttons.addButton(b, QDialogButtonBox.ButtonRole.ActionRole)
        grid.addWidget(buttons)
        self.setLayout(grid)

    def tags(self):
        self.parent().manage_task_tags(self.papernum, self.question, parent=self)

    def flag(self):
        d = WarningQuestion(
            self,
            review_beta_warning,
            question="Are you sure you want to flag this for review?",
        )
        if not d.exec() == QMessageBox.StandardButton.Yes:
            return
        self.parent().flag_question_for_review(self.papernum, self.question, self.who)


class ReviewViewWindowID(QDialog):
    """View image and ask a Yes/No question about reviewing."""

    def __init__(self, parent, fnames):
        super().__init__(parent)
        img = ImageViewWidget(self, fnames, dark_background=True)
        self.setWindowTitle("Does this ID need reviewing?")

        explanation = QLabel(review_beta_warning)
        explanation.setWordWrap(True)

        grid = QVBoxLayout()
        grid.addWidget(img, 1)
        grid.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        b = QPushButton("Yes, &flag for review")
        b.clicked.connect(self.accept)
        buttons.addButton(b, QDialogButtonBox.ButtonRole.YesRole)
        buttons.rejected.connect(self.reject)
        grid.addWidget(buttons)
        self.setLayout(grid)
