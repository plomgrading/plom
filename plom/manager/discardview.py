# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from plom.client import ImageViewWidget


class DiscardViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames):
        super().__init__(parent)
        self.img = ImageViewWidget(self, fnames, has_reset_button=False)
        self.setWindowTitle("Restore discarded page?")

        resetB = QPushButton("reset view")
        moveB = QPushButton("&Move to unknown pages")
        moveB.clicked.connect(self.accept)
        cancelB = QPushButton("&Cancel")
        cancelB.clicked.connect(self.reject)
        resetB.clicked.connect(lambda: self.img.resetView())
        resetB.setAutoDefault(False)  # return won't click the button by default.

        explanation = QLabel(
            """
            <p>If you wish to restore this discarded page, you can first
            convert it to an unknown page.  Then you will be able to
            attach it to a paper to be marked.</p>
            """
        )
        explanation.setWordWrap(True)

        grid = QVBoxLayout()
        grid.addWidget(self.img, 1)
        grid.addWidget(explanation)
        # probably should use QDialogButtonBox?
        buttons = QHBoxLayout()
        buttons.addWidget(resetB)
        buttons.addSpacing(64)
        buttons.addStretch(1)
        buttons.addWidget(moveB)
        buttons.addWidget(cancelB)
        grid.addLayout(buttons)
        self.setLayout(grid)
