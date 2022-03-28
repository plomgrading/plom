# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from plom.client import ImageViewWidget


class ReviewViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, what="question"):
        super().__init__(parent)
        self.img = ImageViewWidget(self, fnames, dark_background=True)
        self.setWindowTitle(f"Does this {what} need reviewing")

        explanation = QLabel(
            """
            <p>Reviewing is a <em>beta</em> feature; it is not well-tested.
            Use this at your own risk.</p>
            <p>If you do tag this work for review, you'll then need to login
            with the Client using a special "reviewer" account.</p>
            """
        )
        explanation.setWordWrap(True)

        grid = QVBoxLayout()
        grid.addWidget(self.img, 1)
        grid.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        reviewB = QPushButton("Tag for &review")
        reviewB.clicked.connect(self.accept)
        buttons.addButton(reviewB, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        grid.addWidget(buttons)
        self.setLayout(grid)
