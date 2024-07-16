# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald

import html

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
)


class AddRemoveTagDialog(QDialog):
    """A dialog for managing the tags of a task.

    Args:
        parent (QWidget): who should parent this modal dialog.
        current_tags (list): the current tags to be laid out for
            deletion.
        tag_choices (list): any explicit choices for new tags, although
            free-form choices can also be made.

    Keyword Args:
        label (str): a short description of what we're tagging, such
            as ``"Paper 7"`` or ``32 questions``.  Used to construct
            dialog titles and prompts.

    Uses the usual `accept()` `reject()` mechanism but on accept you'll need
    to check `.return_values` which is a tuple of `("add", new_tag)` or
    `("remove", tag)`.  In either case the latter is a string.

    Note this dialog does not actually change the tag: the caller needs to
    do that.
    """

    def __init__(self, parent, current_tags, tag_choices, *, label=""):
        super().__init__(parent)

        if label:
            self.from_label = f" from {label}"
        else:
            self.from_label = ""
        self.setWindowTitle(f"Add/remove a tag{self.from_label}")
        self.return_values = None

        flay = QFormLayout()
        # flay = QVBoxLayout

        def remove_func_factory(button, tag):
            def remove_func():
                self.remove_tag(tag)

            return remove_func

        if not current_tags:
            flay.addRow(QLabel("<p><b>No current tags</b></p>"))
        else:
            flay.addRow(QLabel("Current tags:"))
            flay.addItem(
                QSpacerItem(
                    20,
                    4,
                    QSizePolicy.Policy.Minimum,
                    QSizePolicy.Policy.MinimumExpanding,
                )
            )
            for tag in current_tags:
                safe_tag = html.escape(tag)
                row = QHBoxLayout()
                row.addItem(QSpacerItem(48, 1))
                row.addWidget(QLabel(f"<big><em>{safe_tag}</em></big>"))
                b = QToolButton()
                b.setText("\N{ERASE TO THE LEFT}")
                # b.setText("\N{Cross Mark}")
                # b.setText("\N{Multiplication Sign}")
                b.setToolTip(f'Remove tag "{safe_tag}"')
                # important that this callback uses tag not safe_tag:
                b.clicked.connect(remove_func_factory(b, tag))
                row.addWidget(b)
                row.addItem(
                    QSpacerItem(
                        48,
                        1,
                        QSizePolicy.Policy.MinimumExpanding,
                        QSizePolicy.Policy.Minimum,
                    )
                )
                flay.addRow(row)
        flay.addItem(
            QSpacerItem(
                20, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding
            )
        )
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        flay.addRow(line)
        flay.addItem(
            QSpacerItem(
                20, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding
            )
        )
        q = QComboBox()
        q.setEditable(True)
        q.addItem("")
        normal_tags = [t for t in tag_choices if not t.startswith("@")]
        user_tags = [t for t in tag_choices if t.startswith("@")]
        q.addItems(normal_tags)
        q.insertSeparator(len(normal_tags) + 1)
        q.addItems(user_tags)
        flay.addRow("Add new tag", q)
        self.CBadd = q

        flay.addItem(
            QSpacerItem(
                20, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding
            )
        )

        # TODO: cannot tab to OK
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        buttons.accepted.connect(self.add_tag)
        buttons.rejected.connect(self.reject)
        self.CBadd.setFocus()

    def add_tag(self):
        self.return_values = ("add", self.CBadd.currentText())
        self.accept()

    def remove_tag(self, tag):
        safe_tag = html.escape(tag)
        msg = f"<p>Do you want to remove tag &ldquo;{safe_tag}&rdquo;?"
        title = f"Remove tag \u201c{safe_tag}\u201d{self.from_label}?"
        if QMessageBox.question(self, title, msg) != QMessageBox.StandardButton.Yes:
            return
        self.return_values = ("remove", tag)
        self.accept()
