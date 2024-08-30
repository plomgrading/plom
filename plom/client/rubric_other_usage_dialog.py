# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import re
from typing import Any

from PyQt6.QtWidgets import (
    QDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QDialogButtonBox,
)

from .rubrics import render_rubric_as_html


class RubricOtherUsageDialog(QDialog):
    def __init__(
        self,
        parent,
        tasks: list[dict[str, Any]],
        *,
        rubric: dict[str, Any] | None = None,
    ) -> None:
        """Constructor of the dialog to view papers using a rubric.

        Note: the paper numbers in the dialog should have been sorted
        in ascending order.

        Args:
            parent: an Annotator instance.
            tasks: a list of dicts with various fields, notably "code"
               "version", etc.

        Keyword Args:
            rubric: the key-value description of the rubric we're discussing.

        Returns:
            None
        """
        super().__init__(parent)
        self._annotr = parent
        self.setModal(True)

        if rubric:
            self.setWindowTitle(f'Other tasks that use Rubric-ID {rubric["rid"]}')
        else:
            self.setWindowTitle("Other tasks that use the rubric")

        if rubric:
            label1 = QLabel(render_rubric_as_html(rubric))

        label2 = QLabel("Tasks that used this rubric:")
        self.list_widget = QListWidget()
        # Connect double click to view paper
        self.list_widget.itemDoubleClicked.connect(self._handle_double_click)

        # future-proof a bit for when we don't need to strip the leading q
        def noq(code):
            if code.startswith("q"):
                code = code[1:]
            return code

        # TODO: easy to put "by Jose, 10 minutes ago" here...?
        # TODO: only note version if this is a multiversion test?
        list_of_strings = [
            f'{noq(t["code"])} by {t["assigned_user"]} (version {t["question_version"]})'
            for t in tasks
        ]
        list_of_strings.sort()
        self.list_widget.addItems(list_of_strings)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        # Mypy worries ok_button can be None
        assert ok_button
        ok_button.setText("View")

        # Create the view button
        buttons.accepted.connect(self.view_paper)
        buttons.rejected.connect(self.close)

        # Layouts
        v_layout = QVBoxLayout()
        if rubric:
            v_layout.addWidget(label1)
        v_layout.addWidget(label2)
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
        s = selected_items[0].text()
        # extract digits from beginning of string, roughly s[0:4]
        (s,) = re.findall(r"^(\d+)\D", s)
        paper_number = int(s)
        # TODO: by default, the new popup would parent to Annotator
        # self._annotr.view_other_paper(paper_number)
        self._annotr.view_other_paper(paper_number, _parent=self)
