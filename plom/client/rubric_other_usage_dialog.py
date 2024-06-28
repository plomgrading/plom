# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QDialogButtonBox,
)


class RubricOtherUsageDialog(QDialog):
    def __init__(self, parent, paper_numbers: list[int]):
        """Constructor of the dialog to view papers using a rubric.

        Note: the paper numbers in the dialog should have been sorted
        in ascending order.

        Args:
            parent: an Annotator instance.
            paper_numbers: the list of paper numbers that commonly use a rubric.

        Returns:
            None
        """
        super().__init__(parent)
        self._annotr = parent
        self.setModal(True)

        self.setWindowTitle("Other rubric usages")

        # Create a label for the list
        self.label = QLabel("Paper Numbers:")

        # Create the list widget
        self.list_widget = QListWidget()
        # Connect double click to view paper
        self.list_widget.itemDoubleClicked.connect(self._handle_double_click)
        paper_numbers.sort()
        for number in paper_numbers:
            self.list_widget.addItem(str(number))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)

        # for mypy type-checking. Mypy worries ok_button can be None
        if not ok_button:
            raise RuntimeError("There should be ok button.")

        ok_button.setText("View")

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

    def _handle_double_click(self, item):
        self.view_paper()

    def view_paper(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "No Selection", "Please select a paper number to view."
            )
            return
        paper_number = int(selected_items[0].text())
        # TODO: by default, the new popup would parent to Annotator
        # self._annotr.view_other_paper(paper_number)
        self._annotr.view_other_paper(paper_number, _parent=self)
