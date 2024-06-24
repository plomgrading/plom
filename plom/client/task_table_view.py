# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QContextMenuEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTableView,
)


class TaskTableView(QTableView):
    """A table-view widget that emits annotateSignal when the user hits enter or return."""

    # Note: marker.ui knows about this via a "plom/client/task_table_view.h" header

    # This is picked up by the marker, lets it know to annotate
    annotateSignal = pyqtSignal()

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
        # If user hits enter or return, then fire off
        # the annotateSignal, else pass the event on.
        key = event.key()
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.annotateSignal.emit()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        a = QAction("Tag task...", self)
        a.triggered.connect(lambda: print("TODO: tag..."))
        menu.addAction(a)
        a = QAction("Claim this task", self)
        a.triggered.connect(lambda: print("TODO: claim"))
        menu.addAction(a)
        a = QAction("Reassign task to...", self)
        a.triggered.connect(lambda: print("TODO: reassign to..."))
        menu.addAction(a)

        menu.popup(QCursor.pos())
        event.accept()
