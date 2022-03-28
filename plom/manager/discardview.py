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


class DiscardViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames):
        super().__init__(parent)
        self.img = ImageViewWidget(self, fnames)
        self.setWindowTitle("Restore discarded page?")

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
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        moveB = QPushButton("&Move to unknown pages")
        moveB.clicked.connect(self.accept)
        buttons.addButton(moveB, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        grid.addWidget(buttons)
        self.setLayout(grid)
