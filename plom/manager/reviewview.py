# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from plom.client import ImageViewWidget
from plom.client.useful_classes import SimpleQuestion


class ReviewViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, *, what="question", stuff=None):
        super().__init__(parent)
        img = ImageViewWidget(self, fnames, dark_background=True)
        self.setWindowTitle(f"Does this {what} need reviewing?")

        self.papernum, self.question, self.who = stuff
        # TODO: need the display question label TODO: Look up issue #
        explanation = QLabel(
            f"""
            <p>Paper {self.papernum} question {self.question}</p>
            <p>Graded by: {self.who}</p>
            """
        )
        explanation.setWordWrap(True)

        grid = QVBoxLayout()
        grid.addWidget(img, 1)
        grid.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        b = QPushButton("Flag for &review")
        b.clicked.connect(self.flag)
        buttons.addButton(b, QDialogButtonBox.ActionRole)
        b = QPushButton("&Tags...")
        b.clicked.connect(self.tags)
        buttons.addButton(b, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        grid.addWidget(buttons)
        self.setLayout(grid)

    def tags(self):
        self.parent().manage_task_tags(self.papernum, self.question, parent=self)

    def flag(self):
        d = SimpleQuestion(
            self,
            "Are you sure?",
            question="""
                <p>Reviewing is a <em>beta</em> feature; it is not well-tested.
                Use this at your own risk!</p>
                <p>If you do flag this work for review, you'll then need to login
                with the Client using a special "reviewer" account.</p>
            """,
        )
        if not d.exec() == QMessageBox.Yes:
            return
        self.parent().flag_question_for_review(self.papernum, self.question, self.who)
