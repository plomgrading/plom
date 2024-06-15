# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from PyQt6.QtWidgets import (
    QDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QDialogButtonBox,
)
from typing import List


class RubricUsageDialog(QDialog):
    def __init__(self, parent, paper_numbers: List[int]):
        """Constructor of the dialog to view papers using a rubric.

        Note: the paper numbers in the dialog should have been sorted
        in ascending order.

        Args:
            parent: RubricWidget.
            paper_numbers: the list of paper numbers that commonly use a rubric.
        """
        super().__init__()
        self._parent = parent

        self.setWindowTitle("Other rubric usages")

        # Create a label for the list
        self.label = QLabel("Paper Numbers:")

        # Create the list widget
        self.list_widget = QListWidget()
        paper_numbers.sort()
        for number in paper_numbers:
            self.list_widget.addItem(str(number))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)

        # for mypy type-checking. Mypy worries ok_button can be None
        if ok_button:
            ok_button.setText("View")
        else:
            raise RuntimeError("There should be ok button.")

        # Create the view button
        buttons.accepted.connect(self.view_paper)
        buttons.rejected.connect(self.close)

        # Layouts
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.label)
        v_layout.addWidget(self.list_widget)

        h_layout = QHBoxLayout()
        h_layout.addStretch()
        v_layout.addLayout(h_layout)
        self.setLayout(v_layout)

        h_layout.addWidget(buttons)

    def view_paper(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "No Selection", "Please select a paper number to view."
            )
            return
        paper_number = int(selected_items[0].text())
        self._parent.view_other_paper(paper_number)
