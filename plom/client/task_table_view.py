# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QContextMenuEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTableView,
)


class TaskTableView(QTableView):
    """A table-view widget for local storage/presentation of tasks.

    It emits various signals including `annotateSignal` when the user
    hits enter or return.
    """

    # Note: marker.ui knows about this via a "plom/client/task_table_view.h" header

    # Marker will need to connect to these
    annotateSignal = pyqtSignal()
    tagSignal = pyqtSignal()
    claimSignal = pyqtSignal()
    deferSignal = pyqtSignal()
    reassignSignal = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        # User can sort, cannot edit, selects by rows.
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Resize to fit the contents
        self.resizeRowsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def keyPressEvent(self, event):
        """Emit the annotateSignal on Return/Enter key, else pass the event onwards."""
        key = event.key()
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.annotateSignal.emit()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:
        """Open a context menu with options for the currently highlighted task."""
        if not event:
            return
        menu = QMenu(self)
        a = QAction("Annotate\tEnter", self)
        a.triggered.connect(self.annotateSignal.emit)
        menu.addAction(a)
        a = QAction("Tag task", self)
        a.triggered.connect(self.tagSignal.emit)
        menu.addAction(a)
        # TODO: this menu could be "context aware", not showing
        # claim if we already own it or defer if we don't
        a = QAction("Claim this task", self)
        a.triggered.connect(self.claimSignal.emit)
        menu.addAction(a)
        a = QAction("Defer this task", self)
        a.triggered.connect(self.deferSignal.emit)
        menu.addAction(a)
        # a = QAction("Reassign task to...", self)
        # a.triggered.connect(self.reassignSignal.emit)
        # menu.addAction(a)
        menu.popup(QCursor.pos())
        event.accept()
