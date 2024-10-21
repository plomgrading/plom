# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Forest Kobayashi
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from datetime import datetime
import logging
import random  # optionally used for debugging
from typing import Any, Sequence

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCursor, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QInputDialog,
    QGridLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from plom.misc_utils import next_in_longest_subsequence
from .useful_classes import SimpleQuestion, ErrorMsg, InfoMsg, WarnMsg
from .useful_classes import BigMessageDialog
from .rubric_wrangler import RubricWrangler
from .rubrics import compute_score, diff_rubric, render_rubric_as_html
from .rubric_add_dialog import AddRubricBox
from .rubric_other_usage_dialog import RubricOtherUsageDialog

from .rubric_conflict_dialog import RubricConflictDialog
from plom.plom_exceptions import (
    PlomConflict,
    PlomInconsistentRubric,
    PlomNoPermission,
    PlomNoRubric,
    PlomNoServerSupportException,
)


log = logging.getLogger("annotr")


def rubric_is_naked_delta(r: dict[str, Any]) -> bool:
    if r["kind"] == "relative" and r["text"] == ".":
        return True
    return False


def isLegalRubric(rubric: dict[str, Any], *, scene, version: int, max_mark: int) -> int:
    """Checks the 'legality' of a particular rubric - returning one of several possible indicators.

    Those states are:
    0 = incompatible - the kind of rubric is not compatible with the current state
    1 = compatible but out of range - the kind of rubric is compatible with
        the state but applying that rubric will take the score out of range
        [0, max_mark] (so cannot be used).
    2 = compatible and in range - is compatible and can be used.
    3 = version does not match - should be hidden by default.
    Note that the rubric lists use the result to decide which rubrics will
    be shown (2), hidden (0, 3) and greyed out (1)

    Args:
        rubric: a particular rubric to check.

    Keyword Args:
        scene (PageScene): we'll grab the in-use rubrics from it
        max_mark: maximum possible score on this question.
        version: which version.

    Returns:
        integer 0, 1, 2, or 3 as documented above.
    """
    if rubric["versions"]:
        if version not in rubric["versions"]:
            return 3

    if not scene:
        return 2

    rubrics = scene.get_rubrics()
    rubrics.append(rubric)

    try:
        _ = compute_score(rubrics, max_mark)
        return 2
    except ValueError:
        return 1
    except PlomInconsistentRubric:
        return 0


def render_params(
    template: str,
    params: Sequence[tuple[str, Sequence[str]]],
    ver: int,
) -> str:
    """Perform version-dependent substitutions on a template text."""
    s = template
    for param, values in params:
        s = s.replace(param, values[ver - 1])
    return s


class RubricTable(QTableWidget):
    """A RubricTable is presents a table of rubrics.

    There are different types of tabs.  In theory this could be
    implemented as subclasses but currently we just use a property
    ``.tabType``.
    """

    def __init__(
        self,
        parent: RubricWidget,
        shortname: str,
        *,
        sort: bool = False,
        tabType: str | None = None,
    ):
        """Initialize a new RubricTable.

        Args:
            parent: the parent widget.  Cannot be a general widget, must be a
                RubricWidget (or something like it) because we call methods
                of the parent.  TODO: in principle, can use signals/slots?
            shortname: a short string describing the assessment.

        Keyword Args:
            tabType: controls what type of tab this is:
                "show", "hide", "group", "delta", `None`.
                Here `"show"` is used for the "All" tab, `None` is used
                for custom "user tabs".
            sort: is the tab sorted.

        Returns:
            None
        """
        super().__init__(parent)
        self._parent = parent
        self.tabType = tabType  # to help set menu
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setGridStyle(Qt.PenStyle.DotLine)
        self.setAlternatingRowColors(False)
        #  negative padding is probably b/c of fontsize changes
        self.setStyleSheet(
            """
            QHeaderView::section {
                background-color: palette(window);
                color: palette(dark);
                padding-left: 1px;
                padding-right: -3px;
                border: none;
            }
            QTableView {
                border: none;
            }
        """
        )
        head = self.horizontalHeader()
        if head is not None:
            # it seems during unit tests there isn't one?
            # also it seems explicit `is not None` is required
            head.setVisible(False)
            head.setStretchLastSection(True)
        # Issue #1498: use these for shortcut key indicators?
        head = self.verticalHeader()
        if head is not None:
            # it seems during unit tests there isn't one?
            head.setVisible(False)
            # CSS cannot set relative fontsize
            f = self.font()
            f.setPointSizeF(0.67 * f.pointSizeF())
            head.setFont(f)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        _col_headers = ("RID", "Username", "Delta", "Text")
        self.setColumnCount(len(_col_headers))
        self.setHorizontalHeaderLabels(_col_headers)
        self.hideColumn(0)
        self.hideColumn(1)
        if sort:
            self.setSortingEnabled(True)
        self.shortname = shortname
        self.pressed.connect(self.handleClick)
        # self.itemChanged.connect(self.handleClick)
        self.doubleClicked.connect(self.editRow)

    def set_name(self, newname: str) -> None:
        if self.shortname != newname:
            log.debug("tab %s changing name to %s", self.shortname, newname)
        self.shortname = newname
        # TODO: assumes parent is TabWidget, can we do with signals/slots?
        # More like "If anybody cares, I just changed my name!"
        self._parent.update_tab_names()

    def is_user_tab(self) -> bool:
        """Is this a user-created tab."""
        return self.tabType is None

    def is_group_tab(self) -> bool:
        return self.tabType == "group"

    def is_delta_tab(self) -> bool:
        """Is this a one of the delta tabs."""
        return self.tabType == "delta"

    def is_hidden_tab(self) -> bool:
        # TODO: naming here is confusing
        return self.tabType == "hide"

    def is_shared_tab(self) -> bool:
        return self.tabType == "show"

    def contextMenuEvent(self, event):
        """Delegate the context menu to appropriate function."""
        if self.is_hidden_tab():
            self.hideContextMenuEvent(event)
        elif self.is_shared_tab():
            self.showContextMenuEvent(event)
        elif self.is_user_tab():
            self.defaultContextMenuEvent(event)
        elif self.is_delta_tab():
            self.tabContextMenuEvent(event)
        elif self.is_group_tab():
            self.showContextMenuEvent(event)
        else:
            event.ignore()

    def tabContextMenuEvent(self, event):
        menu = QMenu(self)
        a = QAction("Add new tab", self)
        a.triggered.connect(lambda: self._parent.add_new_tab())
        menu.addAction(a)
        menu.popup(QCursor.pos())
        event.accept()

    def defaultContextMenuEvent(self, event):
        # first try to get the row from the event
        row = self.rowAt(event.pos().y())
        if row < 0:
            # no row under click but maybe one is highlighted
            row = self.getCurrentRubricRow()
        rid = None if row is None else self._get_rid_from_row(row)

        # These are workaround for Issue #1441, lambdas in a loop
        def add_func_factory(t, k: int):
            def add_func():
                t.append_by_rid(k)

            return add_func

        def del_func_factory(t, k: int):
            def del_func():
                t.remove_rubric_by_rid(k)

            return del_func

        def edit_func_factory(t, k: int):
            def edit_func():
                t._parent.edit_rubric(k)

            return edit_func

        menu = QMenu(self)
        if rid:
            a = QAction("Edit rubric", self)
            a.triggered.connect(edit_func_factory(self, rid))
            menu.addAction(a)
            menu.addSeparator()

            for tab in self._parent.user_tabs:
                if tab == self:
                    continue
                a = QAction(f"Move to tab {tab.shortname}", self)
                a.triggered.connect(add_func_factory(tab, rid))
                a.triggered.connect(del_func_factory(self, rid))
                menu.addAction(a)
            menu.addSeparator()

            remAction = QAction("Remove from this tab", self)
            remAction.triggered.connect(del_func_factory(self, rid))
            menu.addAction(remAction)
            menu.addSeparator()

        a = QAction("Rename this tab...", self)
        a.triggered.connect(self._parent.rename_current_tab)
        menu.addAction(a)
        a = QAction("Add new tab", self)
        a.triggered.connect(self._parent.add_new_tab)
        menu.addAction(a)
        a = QAction("Remove this tab...", self)
        a.triggered.connect(self._parent.remove_current_tab)
        menu.addAction(a)
        menu.popup(QCursor.pos())
        event.accept()

    def showContextMenuEvent(self, event):
        # first try to get the row from the event
        row = self.rowAt(event.pos().y())
        if row < 0:
            # no row under click but maybe one is highlighted
            row = self.getCurrentRubricRow()
        rid = None if row is None else self._get_rid_from_row(row)

        # workaround for Issue #1441, lambdas in a loop
        def add_func_factory(t, k: int):
            def add_func():
                t.append_by_rid(k)

            return add_func

        def edit_func_factory(t, k: int):
            def edit_func():
                t._parent.edit_rubric(k)

            return edit_func

        def other_usage_factory(t, k: int):
            def other_usage():
                t._parent.other_usage(k)

            return other_usage

        menu = QMenu(self)
        if rid:
            a = QAction("Edit rubric", self)
            a.triggered.connect(edit_func_factory(self, rid))
            menu.addAction(a)
            menu.addSeparator()

            # TODO: walk in another order for moveable tabs?
            # [self._parent.RTW.widget(n) for n in range(1, 5)]
            for tab in self._parent.user_tabs:
                a = QAction(f"Add to tab {tab.shortname}", self)
                a.triggered.connect(add_func_factory(tab, rid))
                menu.addAction(a)
            menu.addSeparator()

            other_usage = QAction("See other usage...", self)
            other_usage.triggered.connect(other_usage_factory(self, rid))
            menu.addAction(other_usage)
            menu.addSeparator()

            hideAction = QAction("Hide rubric", self)
            hideAction.triggered.connect(self.hideCurrentRubric)
            menu.addAction(hideAction)
            menu.addSeparator()
        a = QAction("Add new tab", self)
        a.triggered.connect(self._parent.add_new_tab)
        menu.addAction(a)
        menu.popup(QCursor.pos())
        event.accept()

    def hideContextMenuEvent(self, event):
        menu = QMenu(self)
        unhideAction = QAction("Unhide rubric", self)
        unhideAction.triggered.connect(self.unhideCurrentRubric)
        menu.addAction(unhideAction)
        menu.popup(QCursor.pos())
        event.accept()

    def removeCurrentRubric(self) -> None:
        row = self.getCurrentRubricRow()
        if row is None:
            return
        self.removeRow(row)
        self.selectFirstVisibleRubric()
        self.handleClick()

    def remove_rubric_by_rid(self, rid: int) -> None:
        row = self._get_row_from_rid(rid)
        if row is None:
            return
        self.removeRow(row)
        self.selectFirstVisibleRubric()
        self.handleClick()

    def hideCurrentRubric(self) -> None:
        row = self.getCurrentRubricRow()
        if row is None:
            return
        rid = self._get_rid_from_row(row)
        self._parent.hide_rubric_by_rid(rid)
        self.selectFirstVisibleRubric()
        self.handleClick()

    def unhideCurrentRubric(self) -> None:
        row = self.getCurrentRubricRow()
        if row is None:
            return
        rid = self._get_rid_from_row(row)
        self._parent.unhide_rubric_by_rid(rid)
        self.selectFirstVisibleRubric()
        self.handleClick()

    def dropEvent(self, event):
        # fixed drop event using
        # https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget
        if event.source() == self:
            event.setDropAction(Qt.DropAction.CopyAction)
            sourceRow = self.selectedIndexes()[0].row()
            targetRow = self.indexAt(event.position().toPoint()).row()
            if targetRow == -1:  # no row, so drop at end
                targetRow = self.rowCount()
            # Careful about sorting during setItem calls: Issue #2065
            _sorting_enabled = self.isSortingEnabled()
            self.setSortingEnabled(False)
            # insert a new row at position targetRow
            self.insertRow(targetRow)
            # but now - if sourceRow after target row, sourceRow has moved by 1.
            if targetRow < sourceRow:
                sourceRow += 1
            # move items from the sourceRow to the new targetRow
            for col in range(0, self.columnCount()):
                self.setItem(targetRow, col, self.takeItem(sourceRow, col))
            self.selectRow(targetRow)
            self.removeRow(sourceRow)
            self.setSortingEnabled(_sorting_enabled)
            event.accept()

    def append_by_rid(self, rid: int) -> None:
        """Append a rubric to the end of the list.

        If its a dupe, don't add.

        Args:
            rid: the rubric-id, a key associated with a rubric.

        Raises:
            what happens on invalid rid?
        """
        # ensure there is exactly one matching rubric in the list and grab it
        # TODO: should the local storage be a dict to make this easy?
        (rubric,) = [x for x in self._parent.rubrics if x["rid"] == rid]
        self.appendNewRubric(rubric)

    def appendNewRubric(self, rubric: dict[str, Any]) -> None:
        rc = self.rowCount()
        # do sanity check for duplications
        for r in range(rc):
            if self._get_rid_from_row(r) == rubric["rid"]:
                return  # rubric already present
        # is a new rubric, so append it
        # Careful about sorting during setItem calls: Issue #2065
        _sorting_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.insertRow(rc)
        # rubric-ids as string to avoid overflow on legacy servers with long rids
        self.setItem(rc, 0, QTableWidgetItem(str(rubric["rid"])))
        self.setItem(rc, 1, QTableWidgetItem(rubric["username"]))
        self.setItem(rc, 2, QTableWidgetItem(rubric["display_delta"]))

        render = render_params(
            rubric["text"], rubric["parameters"], self._parent.version
        )
        # Does anyone like this special dot sentinel?  Can we just use empty?
        if render == ".":
            render = ""
        self.setItem(rc, 3, QTableWidgetItem(render))
        # set row header
        self.setVerticalHeaderItem(rc, QTableWidgetItem("{}".format(rc + 1)))
        self.colourLegalRubric(rc)
        # set a tooltip over delta that tells user the type of rubric
        item = self.item(rc, 2)
        assert item
        item.setToolTip("{}-rubric".format(rubric["kind"]))
        # set a tooltip that contains tags and meta info when someone hovers over text
        hoverText = ""
        if rubric["tags"] != "":
            hoverText += "Tagged as {}\n".format(rubric["tags"])
        if rubric["meta"] != "":
            hoverText += "{}\n".format(rubric["meta"])
        item = self.item(rc, 3)
        assert item
        item.setToolTip(hoverText.strip())
        self.setSortingEnabled(_sorting_enabled)

    def set_rubrics_by_rids(
        self,
        rubric_list: list[dict[str, Any]],
        rid_list: list[int],
        *,
        alt_order: list[int] | None = None,
    ) -> None:
        """Clear table and re-populate rubrics, keep selection if possible.

        Args:
            rubric_list: all the rubrics, which are dicts with
                various keys, most notably for us, ``rid``.
            rid_list: which ``rid``s should insert into the table.
                Any ids that missing in `rubric_list` will simply be
                skipped.

        Keyword Args:
            alt_order: use this order instead of `rid_list`.
                But ignore anything in `alt_order` that isn't in `rid_list`.
                Anything that isn't in `alt_order` but is in `rid_list`
                should appear at the end of the list.
                Defaults to None, which means just use the `rid_list`
                order.

        Returns:
            None
        """
        if alt_order:
            # construct a new list from alt_order and rid_list
            new_list = []
            for x in alt_order:
                if x in rid_list:
                    new_list.append(x)
            for x in rid_list:
                if x not in new_list:
                    new_list.append(x)
            rid_list = new_list
        self._set_rubrics_by_rids(rubric_list, rid_list)

    def _set_rubrics_by_rids(
        self, rubric_list: list[dict[str, Any]], rid_list: list[int]
    ) -> None:
        prev_selected_rid = self.getCurrentRubricId()
        # remove everything
        for r in range(self.rowCount()):
            self.removeRow(0)
        # since populating in order of rid_list, build all rid from rubric_list
        rkl = [X["rid"] for X in rubric_list]
        for i in rid_list:
            try:  # guard against mysterious rid
                rb = rubric_list[rkl.index(i)]
            except (ValueError, KeyError, IndexError):
                continue
            self.appendNewRubric(rb)
        if not self.selectRubricById(prev_selected_rid):
            self.selectFirstVisibleRubric()
        self.resizeColumnsToContents()

    def setDeltaRubrics(self, rubrics: list[dict[str, Any]], *, positive=True) -> None:
        """Clear table and repopulate with delta-rubrics, keep selection if possible."""
        prev_selected_rubric_id = self.getCurrentRubricId()
        # remove everything
        for r in range(self.rowCount()):
            self.removeRow(0)
        # grab the delta-rubrics from the rubricslist
        delta_rubrics = []
        for rb in rubrics:
            if rubric_is_naked_delta(rb):
                if (positive and rb["value"] > 0) or (not positive and rb["value"] < 0):
                    delta_rubrics.append(rb)

        # now sort in numerical order away from 0 and add
        for rb in sorted(delta_rubrics, key=lambda r: abs(r["value"])):
            self.appendNewRubric(rb)
        # finally append the manager-created absolute rubrics
        # TODO: bit fragile, but roughly we want the "0 of 10" etc
        for rb in rubrics:
            if rb["system_rubric"] and rb["kind"] == "absolute":
                self.appendNewRubric(rb)
        if not self.selectRubricById(prev_selected_rubric_id):
            self.selectFirstVisibleRubric()
        self.resizeColumnsToContents()

    def get_rid_list(self) -> list[int]:
        """Get the list of all rubric-id in this table."""
        return [self._get_rid_from_row(r) for r in range(self.rowCount())]

    def _get_rid_from_row(self, r: int) -> int:
        item = self.item(r, 0)
        # TODO: is an assertion error what we want here?
        assert item, f"Could not find row {r}"
        return int(item.text())

    def _get_row_from_rid(self, rid: int) -> int | None:
        for r in range(self.rowCount()):
            if self._get_rid_from_row(r) == rid:
                return r
        else:
            return None

    def getCurrentRubricRow(self) -> int | None:
        if not self.selectedIndexes():
            return None
        return self.selectedIndexes()[0].row()

    def getCurrentRubricId(self) -> int | None:
        """Get the currently selected rubric's key/id or None if nothing is selected."""
        if not self.selectedIndexes():
            return None
        return self._get_rid_from_row(self.selectedIndexes()[0].row())

    def reselectCurrentRubric(self) -> None:
        """Reselect the current rubric row, triggering redraws (for example).

        If no selected row, then select the first visible row, or perhaps
        no row if there are no rows.
        """
        r = self.getCurrentRubricRow()
        if r is None:
            self.selectFirstVisibleRubric()
            return
        self.selectRubricByRow(r)

    def selectRubricByRow(self, r: int | None) -> None:
        """Select the r'th rubric in the list.

        Args:
            r: The row-number in the rubric-table.
                If r is None, do nothing.
        """
        if r is not None:
            self.selectRow(r)

    def selectRubricByVisibleRow(self, r: int) -> None:
        """Select the r'th **visible** row.

        Args:
            r: The row-number in the rubric-table.

        If r is out-of-range, then do nothing.  If there are no rows,
        do nothing.
        """
        rc = -1  # start here, so that correctly test after-increment
        for s in range(self.rowCount()):
            if not self.isRowHidden(s):
                rc += 1
            if rc == r:
                self.selectRow(s)
                return

    def selectFirstVisibleRubric(self) -> None:
        """Select the first visible row.

        If there are no rows, or no visible rows, then do nothing.
        """
        self.selectRubricByVisibleRow(0)

    def selectRubricById(self, rid: int | None) -> bool:
        """Select row with given rubric-id, returning True if works, else False."""
        if rid is None:
            return False
        for r in range(self.rowCount()):
            if self._get_rid_from_row(r) == rid:
                self.selectRow(r)
                return True
        return False

    def nextRubric(self) -> None:
        """Move selection to the next row, wrapping around if needed."""
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() >= 1:
                self.selectFirstVisibleRubric()
                self.handleClick()  # actually force a click
            return
        rs = r  # get start row
        while True:  # move until we get back to start or hit unhidden row
            r = (r + 1) % self.rowCount()
            if r == rs or not self.isRowHidden(r):
                break
        self.selectRubricByRow(r)  # we know that row is not hidden
        self.handleClick()

    def previousRubric(self) -> None:
        """Move selection to the previous row, wrapping around if needed."""
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() >= 1:
                self.selectRubricByRow(self.lastUnhiddenRow())
            return
        rs = r  # get start row
        while True:  # move until we get back to start or hit unhidden row
            r = (r - 1) % self.rowCount()
            if r == rs or not self.isRowHidden(r):
                break
        self.selectRubricByRow(r)
        self.handleClick()

    def handleClick(self) -> None:
        # When an item is clicked, grab the details and emit rubric signal
        r = self.getCurrentRubricRow()
        if r is None:
            r = self.firstUnhiddenRow()
            if r is None:  # there is nothing unhidden here.
                return
            self.selectRubricByRow(r)

        rubric = self.get_row_as_rubric(r).copy()
        rubric["text"] = render_params(
            rubric["text"], rubric["parameters"], self._parent.version
        )
        self._parent.rubricSignal.emit(rubric)

    def get_row_as_rubric(self, r: int) -> dict[str, Any]:
        """Get the rth row of the rubric table."""
        item = self.item(r, 0)
        assert item
        rid = int(item.text())
        for rubric in self._parent.rubrics:
            if rubric["rid"] == rid:
                return rubric
        raise RuntimeError(f"Cannot find rubric {rid}. Corrupted rubric lists?")

    def firstUnhiddenRow(self) -> int | None:
        for r in range(self.rowCount()):
            if not self.isRowHidden(r):
                return r
        return None

    def lastUnhiddenRow(self) -> int | None:
        for r in reversed(range(self.rowCount())):
            if not self.isRowHidden(r):
                return r
        return None

    def colourLegalRubric(self, r: int) -> None:
        legal = isLegalRubric(
            self.get_row_as_rubric(r),
            scene=self._parent._parent.scene,
            version=self._parent.version,
            max_mark=self._parent.max_mark,
        )
        colour_legal = self.palette().color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Text
        )
        colour_illegal = self.palette().color(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text
        )
        # colour_hide = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        if legal == 2:
            self.showRow(r)
            for item in (self.item(r, 2), self.item(r, 3)):
                assert item is not None
                item.setForeground(colour_legal)
        elif legal == 1:
            self.showRow(r)
            for item in (self.item(r, 2), self.item(r, 3)):
                assert item is not None
                item.setForeground(colour_illegal)
        else:
            self.hideRow(r)
            # self.showRow(r)
            # self.item(r, 2).setForeground(colour_hide)
            # self.item(r, 3).setForeground(colour_hide)

    def updateLegality(self) -> None:
        """Style items according to their legality."""
        for r in range(self.rowCount()):
            self.colourLegalRubric(r)

    def editRow(self, tableIndex) -> None:
        rid = self._get_rid_from_row(tableIndex.row())
        self._parent.edit_rubric(rid)


class TabBarWithAddRenameRemoveContext(QTabBar):
    """A QTabBar with a context right-click menu for add/rename/remove tabs.

    Has slots for add, renaming and removing tabs:

    * add_tab_signal
    * rename_tab_signal
    * remove_tab_signal
    """

    add_tab_signal = pyqtSignal()
    rename_tab_signal = pyqtSignal(int)
    remove_tab_signal = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()

    def mousePressEvent(self, mouseEvent):
        if mouseEvent.button() == Qt.MouseButton.RightButton:
            point = mouseEvent.pos()
            n = self.tabAt(point)
            if n >= 0:
                name = self.tabText(n)
                tabtype = self.tabData(n)
                menu = QMenu()
                a = menu.addAction(
                    f'Rename tab "{name}"...', lambda: self.rename_tab_signal.emit(n)
                )
                if tabtype is not None:
                    a.setEnabled(False)
                a = menu.addAction(
                    f'Remove tab "{name}"...', lambda: self.remove_tab_signal.emit(n)
                )
                if tabtype is not None:
                    a.setEnabled(False)
                menu.addAction("Add new tab", self.add_tab_signal.emit)
                menu.exec(self.mapToGlobal(point))
        super().mousePressEvent(mouseEvent)


class RubricTabWidget(QTabWidget):
    """A TabWidget that contains only RubricTables in the tabs."""

    def __init__(self, add_new_tab_fcn, rename_tab_fcn, remove_tab_fcn) -> None:
        super().__init__()
        tb = TabBarWithAddRenameRemoveContext()
        tb.setChangeCurrentOnDrag(True)
        self.setTabBar(tb)
        self.setMovable(True)
        tb.add_tab_signal.connect(add_new_tab_fcn)
        tb.rename_tab_signal.connect(rename_tab_fcn)
        tb.remove_tab_signal.connect(remove_tab_fcn)

    def insertTab(self, *args, **kwargs):
        """Override and prevent the usual way of adding tabs."""
        raise RuntimeError("You must use our `insert_rubric_tab` instead")

    def insert_rubric_tab(self, index: int, tab: RubricTable) -> int:
        """Add a new RubricTable to this tab widget, used instead of superclass's insertTab."""
        # assert isinstance(widget, RubricTable)
        r = super().insertTab(index, tab, tab.shortname)
        tb = self.tabBar()
        assert tb
        tb.setTabData(index, tab.tabType)
        return r

    def currentWidget(self) -> RubricTable:
        """Override the superclass method, mainly for typing to tell callers we return a RubricTable."""
        w = super().currentWidget()
        assert isinstance(w, RubricTable)
        return w

    def widget(self, index: int) -> RubricTable | None:
        """Override the widget method to promise to give a RubricTable (or None).

        Note: because this can return None, and we often do an integer index loop,
        tools like MyPy can be confused whether the typeis RubricTable or None.
        In many places we use `assert` or even `ignore[union-attr]`.
        """
        w = super().widget(index)
        if w is None:
            return None
        assert isinstance(w, RubricTable)
        return w

    def _update_tab_names(self) -> None:
        """Loop over the tabs and update their displayed names."""
        tb = self.tabBar()
        assert tb
        for n in range(self.count()):
            tab = self.widget(n)
            assert tab
            self.setTabText(n, tab.shortname)
            tb.setTabData(n, tab.tabType)
            # colours that seem vaguely visible in both light/dark theme: "teal", "olive"
            if tab.is_user_tab():
                self.setTabToolTip(n, "custom tab")
                # TODO: blend green with palette color?
                tb.setTabTextColor(n, QColor("teal"))
            elif tab.is_group_tab():
                self.setTabToolTip(n, "shared group")
                # maybe no need to highlight shared tabs?
                # tb.setTabTextColor(n, QColor("olive"))
            # elif tab.is_shared_tab():
            #     self.setTabToolTip(n, "All rubrics")
            # elif tab.is_delta_tab():
            #     self.setTabToolTip(n, "delta")


class RubricWidget(QWidget):
    """The RubricWidget is a multi-tab interface for displaying, choosing and managing rubrics."""

    # This is picked up by the annotator to tell the scene the current rubric
    rubricSignal = pyqtSignal(dict)

    def __init__(self, parent) -> None:
        """Initialize the class.

        Args:
            parent: in theory, a QWidget, but in practice this must be an
                Annotator which is a particular subclass, b/c we will call
                methods from that class.
        """
        super().__init__(parent)
        self.question_label = ""
        self.question_index = 1
        self.version = 1
        self.max_version = 1
        self.max_mark = 1
        self._parent = parent
        self.username = parent.username
        self.rubrics: list[dict[str, Any]] = []

        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        deltaP_label = "+\N{GREEK SMALL LETTER DELTA}"
        deltaN_label = "\N{MINUS SIGN}\N{GREEK SMALL LETTER DELTA}"
        self.tabS = RubricTable(self, shortname="All", tabType="show")
        self.tabDeltaP = RubricTable(self, shortname=deltaP_label, tabType="delta")
        self.tabDeltaN = RubricTable(self, shortname=deltaN_label, tabType="delta")
        self.RTW = RubricTabWidget(self.add_new_tab, self.rename_tab, self.remove_tab)
        self.RTW.insert_rubric_tab(0, self.tabS)
        self.RTW.insert_rubric_tab(1, self.tabDeltaP)
        self.RTW.insert_rubric_tab(2, self.tabDeltaN)
        b = QToolButton()
        b.setText("+")
        b.setAutoRaise(True)  # flat until hover, but not on macOS?
        # Makes it too easy to add too many tabs, Issue #2350
        # b.clicked.connect(self.add_new_tab)
        m = QMenu(b)
        m.addAction("Add new tab", self.add_new_tab)
        m.addAction("Rename current tab...", self.rename_current_tab)
        m.addSeparator()
        m.addAction("Remove current tab...", self.remove_current_tab)
        b.setMenu(m)
        b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.RTW.setCornerWidget(b)
        self.RTW.setCurrentIndex(0)  # start on shared tab
        # connect the 'tab-change'-signal to 'handleClick' to fix #1497
        self.RTW.currentChanged.connect(self.handleClick)

        self.tabHide = RubricTable(self, shortname="Hidden", sort=True, tabType="hide")
        self.groupHide = QTabWidget()
        self.groupHide.addTab(self.tabHide, "Hidden")
        self.showHideW = QStackedWidget()
        self.showHideW.addWidget(self.RTW)
        self.showHideW.addWidget(self.groupHide)
        grid.addWidget(self.showHideW, 1, 1, 2, 4)
        self.addB = QPushButton("&Add")  # faster debugging, could remove?
        self.filtB = QPushButton("Arrange/Filter")
        self.hideB = QPushButton("Shown/Hidden")
        self.syncB = QPushButton()
        # self.syncB.setText("\N{Rightwards Harpoon Over Leftwards Harpoon}")
        self.syncB.setText("Sync")
        self.syncB.setToolTip("Synchronise rubrics")
        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.filtB, 3, 2)
        grid.addWidget(self.hideB, 3, 3)
        grid.addWidget(self.syncB, 3, 4)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.add_new_rubric)
        self.filtB.clicked.connect(self.wrangleRubricsInteractively)
        self.syncB.clicked.connect(self.refreshRubrics)
        self.hideB.clicked.connect(self.toggleShowHide)
        self.update_tab_names()

    def toggleShowHide(self) -> None:
        if self.showHideW.currentIndex() == 0:  # on main lists
            # move to hidden list
            self.showHideW.setCurrentIndex(1)
            # disable a few buttons
            self.addB.setEnabled(False)
            self.filtB.setEnabled(False)
            self.syncB.setEnabled(False)
            # reselect the current rubric
            self.tabHide.handleClick()
        else:
            # move to main list
            self.showHideW.setCurrentIndex(0)
            # enable buttons
            self.addB.setEnabled(True)
            self.filtB.setEnabled(True)
            self.syncB.setEnabled(True)
            # reselect the current rubric
            self.handleClick()

    @property
    def user_tabs(self):
        """Dynamically construct the ordered list of user-defined tabs."""
        return self.get_user_tabs()

    def get_user_tabs(self) -> list[RubricTable]:
        """Get an ordered list of user-defined tabs."""
        # this is all tabs: we want only the user ones
        # return [self.RTW.widget(n) for n in range(self.RTW.count())]
        L = []
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            assert tab
            if tab.is_user_tab():
                L.append(tab)
        return L

    def get_group_tabs(self) -> list[RubricTable]:
        """Get an ordered list of the group tabs."""
        L = []
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            assert tab
            if tab.is_group_tab():
                L.append(tab)
        return L

    def get_group_tabs_dict(self) -> dict[str, RubricTable]:
        """Get a dict of the group tabs, keyed by name."""
        d = {}
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            assert tab
            if tab.is_group_tab():
                d[tab.shortname] = tab
        return d

    def update_tab_names(self) -> None:
        """Loop over the tabs and update their displayed names."""
        self.RTW._update_tab_names()

    def add_new_group_tab(self, name: str) -> RubricTable:
        """Add new group-defined tab.

        The new tab is inserted after the right-most "group" tab, or
        immediately after the "All" tab if there are no "group" tabs.

        Args:
            name: name of the new tab.

        Returns:
            The newly-created RubricTable.
        """
        tab = RubricTable(self, shortname=name, tabType="group")
        idx = None
        for n in range(0, self.RTW.count()):
            t = self.RTW.widget(n)
            assert t
            if t.is_group_tab():
                idx = n
        if idx is None:
            idx = 0
        # insert tab after that
        self.RTW.insert_rubric_tab(idx + 1, tab)
        self.update_tab_names()
        return tab

    def add_new_tab(self, name: str | None = None) -> None:
        """Add new user-defined tab either to end or near end.

        The new tab is inserted after the right-most non-delta tab.
        For example, the default config has delta tabs at the end; if
        user adds a new tab, it appears before these.  But the user may
        have rearranged the delta tabs left of their custom tabs.

        Args:
            name: the name of the new tab.  If omitted or None,
                generate one from a set of symbols with digits appended
                if necessary.
        """
        if not name:
            empties = []
            for tab in self.get_user_tabs():
                if tab.rowCount() == 0:
                    empties.append(tab.shortname)
            if len(empties) >= 2:
                msg = SimpleQuestion(
                    self,
                    f"You already have {len(empties)} empty custom user tabs: "
                    + ", ".join(f'"{x}"' for x in empties)
                    + ".",
                    question="Add another empty tab?",
                )
                if msg.exec() == QMessageBox.StandardButton.No:
                    return

        if not name:
            tab_names = [x.shortname for x in self.get_user_tabs()]
            name = next_in_longest_subsequence(tab_names)
        if not name:
            syms = (
                "\N{BLACK STAR}",
                "\N{BLACK HEART SUIT}",
                "\N{BLACK SPADE SUIT}",
                "\N{BLACK DIAMOND SUIT}",
                "\N{BLACK CLUB SUIT}",
                "\N{DOUBLE DAGGER}",
                "\N{FLORAL HEART}",
                "\N{ROTATED FLORAL HEART BULLET}",
            )
            extra = ""
            counter = 0
            while not name:
                for s in syms:
                    if s + extra not in tab_names:
                        name = s + extra
                        break
                counter += 1
                extra = f"{counter}"

        tab = RubricTable(self, shortname=name)
        # find rightmost non-delta
        n = self.RTW.count() - 1
        while self.RTW.widget(n).is_delta_tab() and n > 0:  # type: ignore[union-attr]
            n = n - 1
        # insert tab after it
        self.RTW.insert_rubric_tab(n + 1, tab)
        self.update_tab_names()

    def remove_current_tab(self) -> None:
        n = self.RTW.currentIndex()
        self.remove_tab(n)

    def remove_tab(self, n: int) -> None:
        if n < 0:  # -1 means no current tab
            return
        tab = self.RTW.widget(n)
        if not tab:
            return
        if not tab.is_user_tab():  # no removing shared and delta tabs
            return
        # TODO: consider not asking or asking differently if empty?
        if tab.rowCount() > 0:
            msg = "<p>Are you sure you want to delete the "
            msg += f"tab &ldquo;{tab.shortname}&rdquo;?</p>"
            msg += "<p>(The rubrics themselves will not be deleted).<p>"
        else:
            msg = "<p>Are you sure you want to delete the empty "
            msg += f"tab &ldquo;{tab.shortname}&rdquo;?</p>"
        if SimpleQuestion(self, msg).exec() == QMessageBox.StandardButton.No:
            return
        self.RTW.removeTab(n)
        tab.clear()
        tab.deleteLater()

    def rename_current_tab(self) -> None:
        n = self.RTW.currentIndex()
        self.rename_tab(n)

    def rename_tab(self, n: int) -> None:
        if n < 0:  # -1 means no current tab
            return
        tab = self.RTW.widget(n)
        if not tab:
            return
        if not tab.is_user_tab():
            # no renaming the "all" tab, +/- delta or group tabs
            return
        curname = tab.shortname
        s = ""
        while True:
            msg = f"<p>Enter new name for tab &ldquo;{curname}&rdquo;.</p>"
            if s:
                msg = f"<p>There is already a tab named &ldquo;{s}&rdquo;.</p>" + msg
            s, ok = QInputDialog.getText(self, f'Rename tab "{curname}"', msg)
            if not ok or not s:
                return
            for n in range(self.RTW.count()):
                if s == self.RTW.widget(n).shortname:  # type: ignore[union-attr]
                    ok = False
            if ok:
                break

        # TODO: hint that "&nice" will enable "alt-n" shortcut on most OSes
        # TODO: use a custom dialog
        # s2, ok2 = QInputDialog.getText(
        #     self, 'Rename tab "{}"'.format(curname), "Enter long name"
        # )
        log.debug('changing tab name from "%s" to "%s"', curname, s)
        tab.set_name(s)

    def _sync_button_temporary_change_text(self, set: bool = False) -> None:
        tempstr = "Sync \N{CHECK MARK}"
        if set:
            self.syncB.setText(tempstr)
            return
        # don't touch if a background process has adjusted it
        if self.syncB.text() == tempstr:
            self.syncB.setText("Sync")

    def refreshRubrics(self) -> None:
        """Get rubrics from server and if non-trivial then repopulate."""
        old_rubrics = self.rubrics
        self.rubrics = self._parent.getRubricsFromServer()
        self.setRubricTabsFromState(self.get_tab_rubric_lists())
        self._parent.saveTabStateToServer(self.get_tab_rubric_lists())
        old = {r["rid"]: r for r in old_rubrics}
        new = {r["rid"]: r for r in self.rubrics}
        added = []
        changed = []
        deleted = []
        for rid in old.keys():
            if rid not in new.keys():
                deleted.append(rid)
        for rid, r in new.items():
            rold = old.get(rid)
            if rold is None:
                added.append(rid)
                continue
            same, out = diff_rubric(rold, r)
            if not same:
                changed.append((rid, out))
        last_sync_time = datetime.now().strftime("%H:%M")
        self.syncB.setToolTip(f"Rubrics last synchronized at {last_sync_time}")
        if not deleted and not changed and not added:
            # change the label to show user something happened
            self._sync_button_temporary_change_text(set=True)
            # then remove the checkmark a few seconds later
            timer = QTimer()
            timer.singleShot(2000, self._sync_button_temporary_change_text)
        msg = "<p>\N{CHECK MARK} Your tabs have been synced to the server.</p>\n"
        # msg += "<p>No changes to server rubrics.</p>"
        msg += "<p>\N{CHECK MARK} server: "
        msg += f"<b>{len(added)} new</b>, "
        msg += f"<b>{len(deleted)} deleted</b> rubrics.</p>\n"
        d = ""
        if added and deleted:
            d += "<h3>Added/Deleted</h3>\n"
        elif added:
            d += "<h3>Added</h3>\n"
        elif deleted:
            d += "<h3>Deleted</h3>\n"
        if added or deleted:
            d += "<ul>\n"
            for rid in added:
                d += "<li>\n" + render_rubric_as_html(new[rid]) + "</li>\n"
            for rid in deleted:
                d += "<li><b>Deleted: </b>\n"
                d += render_rubric_as_html(old[rid])
                d += "</li>\n"
            d += "</ul>\n"
        msg += "<p>\N{CHECK MARK} server: "
        msg += f"<b>{len(changed)} changed</b> rubrics.</p>\n"
        if changed:
            d += "<h3>Changes</h3>\n"
            d += "<ul>\n"
            for rid, diff in changed:
                d += f"<li>{diff}</li>\n"
            d += "</ul>\n"
        if added or changed or deleted:
            BigMessageDialog(self, msg, details_html=d, show=False).exec()
        # diff_rubric is not precise, won't hurt to update display even if no changes
        self.updateLegalityOfRubrics()

    def wrangleRubricsInteractively(self) -> None:
        wr = RubricWrangler(
            self,
            self.rubrics,
            self.get_tab_rubric_lists(),
            self.username,
            annotator_size=self._parent.size(),
        )
        if wr.exec() != QDialog.DialogCode.Accepted:
            return
        else:
            self.setRubricTabsFromState(wr.wranglerState)

    def setInitialRubrics(self, *, user_tab_state: dict | None = None) -> None:
        """Grab rubrics from server and set sensible initial values.

        Note: must be called after annotator knows its tgv etc, so
        maybe difficult to call from __init__.  TODO: a possible
        refactor would have the caller (which is probably `_parent`)
        get the server rubrics list and pass in as an argument.

        Keyword Args:
            user_tab_state (dict/None): a representation of the state of
                the user's tabs, or None.  If None then pull from server.
                If server also has none, initialize with some empty tabs.
                Note: currently caller always passes None.
        """
        self.rubrics = self._parent.getRubricsFromServer()
        if not user_tab_state:
            user_tab_state = self._parent.getTabStateFromServer()
        if not user_tab_state:
            # no user-state: start with single empty tab
            self.add_new_tab()
        self.setRubricTabsFromState(user_tab_state)

    def setRubricTabsFromState(self, wranglerState: dict | None = None) -> None:
        """Set rubric tabs (but not rubrics themselves) from saved data.

        The various rubric tabs are updated based on data passed in.
        The rubrics themselves are uneffected.  The currently-selected
        rubric in each is preserved, provided that rubric is still
        present.

        Args:
            wranglerState (dict/None): a representation of the state of
                the user's tabs.  This could be from a previous session
                or it could be "stale" in the sense that new rubrics
                have arrived or some have been deleted.  Can be None
                meaning no state.
                The contents must contain lists `shown`, `hidden`,
                `tab_order` and `user_tabs`.
                `user_tabs` is a list of dicts, with `name` and `ids`
                fields.
                Any of these lists could be empty.  The order in
                `user_tabs` is not significant.

        A note about "shown": this is not intended to be the complement of
        "hidden": its used to save the ordering of the "all" tab.  We will
        filter out the contents of "hidden" from "shown" and the other tabs.

        If there is too much data for the number of tabs, the extra data
        is discarded.  If there is too few data, pad with empty lists
        and/or leave the current lists as they are.
        """
        if not wranglerState:
            wranglerState = {
                "shown": [],
                "hidden": [],
                "tab_order": [],
                "user_tabs": [],
                "group_tabs": [],
            }

        # Update the wranglerState for any new rubrics not in shown/hidden (Issue #1493)
        for rubric in self.rubrics:
            # don't add HAL system rubrics: TODO: are there any of these now?
            if rubric["username"] == "HAL":
                continue
            # exclude manager-delta rubrics, see also Issue #1494
            if rubric_is_naked_delta(rubric):
                continue
            if (
                rubric["rid"] not in wranglerState["hidden"]
                and rubric["rid"] not in wranglerState["shown"]
            ):
                log.info("Appending new rubric with id {}".format(rubric["rid"]))
                wranglerState["shown"].append(rubric["rid"])

        group_tab_data: dict[str, list[int]] = {}
        for rubric in self.rubrics:
            tags = rubric.get("tags", "").split()
            # TODO: share pack/unpack from tag w/ dialog & compute_score
            for t in tags:
                g = None
                if t.startswith("group:"):
                    tags.remove(t)
                    # TODO: Python >= 3.9
                    # g = t.removeprefix("group:")
                    g = t[len("group:") :]
                if not g:
                    continue
                if not group_tab_data.get(g):
                    group_tab_data[g] = []
                group_tab_data[g].append(rubric["rid"])

        # Filter any "hidden" rubrics out of "shown", group and user tabs
        for rubric in self.rubrics:
            rid = rubric["rid"]
            if rid not in wranglerState["hidden"]:
                continue
            if rid in wranglerState["shown"]:
                log.debug(f'filtering hidden rubric id {rid} from "all"')
                wranglerState["shown"].remove(rid)
            for n, user_tab in enumerate(wranglerState["user_tabs"]):
                if rid in user_tab["ids"]:
                    log.debug(f"filtering hidden rubric id {rid} from user tab {n}")
                    # Issue #2474, filter anything in the hidden list
                    user_tab["ids"].remove(rid)
            for g, lst in group_tab_data.items():
                if rid in lst:
                    log.debug(f"filtering hidden rubric id {rid} from group {g}")
                    lst.remove(rid)

        # Issue #3006: delete groups with empty lists due to hiding
        group_tab_data = {k: v for k, v in group_tab_data.items() if v}

        current_group_tabs = self.get_group_tabs_dict()
        _group_tabs = wranglerState.get("group_tabs", {})
        prev_group_tabs = {x["name"]: x["ids"] for x in _group_tabs}
        for name, tab in current_group_tabs.items():
            if name not in group_tab_data.keys():
                log.info("Removing now-empty tab: group %s is now empty", name)
                self.RTW.removeTab(self.RTW.indexOf(tab))

        for g in sorted(group_tab_data.keys()):
            idlist = group_tab_data[g]
            gtab = current_group_tabs.get(g)
            if gtab is None:
                gtab = self.add_new_group_tab(g)
            prev_order = prev_group_tabs.get(g)
            gtab.set_rubrics_by_rids(self.rubrics, idlist, alt_order=prev_order)

        # TODO: if we later deleting rubrics, this will need to deal with rubrics that
        # have disappeared from self.rubrics but still appear in some tab

        # Nicer code than below but zip truncates shorter list during length mismatch
        # for tab, name in zip(self.user_tabs, wranglerState["user_tab_names"]):
        #    tab.set_name(name)
        curtabs = self.user_tabs
        newnames = [x["name"] for x in wranglerState["user_tabs"]]

        # prime any names that overlap with group names or are duplicates
        # we want unique tab names; group names could've changed while logged out
        s = set()
        for i, name in enumerate(newnames):
            while name in group_tab_data.keys() or name in s:
                log.warning("renaming user tab %s to %s for conflict", name, name + "'")
                name += "'"
                newnames[i] = name
            s.add(name)

        for n in range(max(len(curtabs), len(newnames))):
            if n < len(curtabs):
                if n < len(newnames):
                    curtabs[n].set_name(newnames[n])
            else:
                if n < len(newnames):
                    self.add_new_tab(newnames[n])
        del curtabs

        for n, tab in enumerate(self.user_tabs):
            if n >= len(wranglerState["user_tabs"]):
                # not enough data for number of tabs
                idlist = []
            else:
                idlist = wranglerState["user_tabs"][n]["ids"]
            tab.set_rubrics_by_rids(self.rubrics, idlist)
        # all rubrics should appear here unless hidden: "shown" is just helping with ordering
        self.tabS.set_rubrics_by_rids(self.rubrics, wranglerState["shown"])
        self.tabDeltaP.setDeltaRubrics(self.rubrics, positive=True)
        self.tabDeltaN.setDeltaRubrics(self.rubrics, positive=False)
        self.tabHide.set_rubrics_by_rids(self.rubrics, wranglerState["hidden"])
        try:
            self.reorder_tabs(wranglerState["tab_order"])
        except AssertionError as e:
            # its not critical to re-order: if it fails just log
            log.error("Unexpected failure sorting tabs: %s", str(e))

        self.update_tab_names()

        # force a blue ghost update
        self.handleClick()

    def reorder_tabs(self, target_order: list[str]) -> None:
        """Change the order of the tabs to match a target order.

        Args:
            target_order: a list of strings for the order we would
                like to see.  We will copy and then dedupe this input.

        Returns:
            None, but modifies the tab order.

        Algorithm probably relies on the tabs having unique names.
        """

        def order_preserving_dedupe(L):
            s = set()
            for i, name in enumerate(L):
                if name in s:
                    L.pop(i)
                else:
                    s.add(name)
            return L

        target_order = target_order.copy()
        target_order = order_preserving_dedupe(target_order)

        # Re-order the tabs in three steps
        # First, introduce anything new into target order, preserving current order
        current = [
            self.RTW.widget(n).shortname  # type: ignore[union-attr]
            for n in range(0, self.RTW.count())
        ]
        assert len(set(current)) == len(current), "Non-unique tab names"
        # debugging: target_order = ["−δ", "(a)", "nosuch", "★", "+δ", "All"]
        # print(f"order: {current}\ntarget order: {target_order}")
        for i, name in enumerate(current):
            if name in target_order:
                continue
            if i == 0:
                target_order.insert(0, name)
                continue
            previous_name = current[i - 1]
            j = target_order.index(previous_name)
            target_order.insert(j + 1, name)
        # Second, prune anything in target no longer in tabs
        for i, name in enumerate(target_order):
            if name not in current:
                target_order.pop(i)
        # print(f"updated target: {target_order}")
        assert len(target_order) == len(current), "Length mismatch"

        # Third, sort according to the target
        i = 0
        iter = 0
        maxiter = (self.RTW.count()) ** 2
        while i < self.RTW.count():
            iter += 1
            assert iter < maxiter, "quadratic iteration cap exceeded"
            current = [
                self.RTW.widget(n).shortname  # type: ignore[union-attr]
                for n in range(0, self.RTW.count())
            ]
            # print((i, current))
            # we know we can find it b/c we just updated target
            j = target_order.index(current[i])
            if i == j:
                # all indices before this are now in the correct order
                i += 1
                continue
            tb = self.RTW.tabBar()
            assert tb
            tb.moveTab(i, j)
        check = [
            self.RTW.widget(n).shortname  # type: ignore[union-attr]
            for n in range(0, self.RTW.count())
        ]
        assert check == target_order, "did not achieve target"

    def getCurrentRubricIdAndTab(self) -> tuple[int | None, int]:
        """The current rubric rid and the current tab.

        Returns:
            Two numbers ``(a, b)`` where ``a`` is the rubric-id
            and ``b`` is the current tab index.  If nothing is selected,
            the rubric-id will be None.
        """
        return (
            self.RTW.currentWidget().getCurrentRubricId(),
            self.RTW.currentIndex(),
        )

    def setCurrentRubricIdAndTab(self, rid: int | None, tab: int) -> bool:
        """Set the current rubric rid and the current tab, as if it was clicked on.

        Args:
            rid: which rubric to highlight.  If None, no action.
            tab: index of which tab to choose.

        Returns:
            True if we set a row, False if we could not find an
            appropriate row b/c for example key or tab are invalid or
            not found.
        """
        if rid is None:
            return False
        if tab not in range(0, self.RTW.count()):
            return False
        self.RTW.setCurrentIndex(tab)
        is_success = self.RTW.currentWidget().selectRubricById(rid)
        self.handleClick()  # force blue ghost update
        return is_success

    def setQuestion(self, qidx: int, label: str, max_mark: int) -> None:
        """Set relevant question index, label and maximum mark.

        Args:
            qidx: the 1-based question index.
            label: the question label.
            max_mark: the maximum mark associated with this question.

        After calling this, you should call ``updateLegalityOfRubrics()`` to
        update which rubrics are highlighted/displayed.
        """
        self.question_index = qidx
        self.question_label = label
        self.max_mark = max_mark

    def setVersion(self, version: int, maxver: int) -> None:
        """Set version being graded.

        Args:
            version: which version.
            maxver: the largest version in this assessment.

        After calling this, you should call ``updateLegalityOfRubrics()`` to
        update which rubrics are highlighted/displayed.
        """
        self.version = version
        self.max_version = maxver

    def updateLegalityOfRubrics(self) -> None:
        """Redo the colour highlight/deemphasis in each tab."""
        self.tabS.updateLegality()
        for tab in self.get_user_tabs():
            tab.updateLegality()
        for tab in self.get_group_tabs():
            tab.updateLegality()
        self.tabDeltaP.updateLegality()
        self.tabDeltaN.updateLegality()

    def handleClick(self) -> None:
        self.RTW.currentWidget().handleClick()

    def reselectCurrentRubric(self) -> None:
        self.RTW.currentWidget().reselectCurrentRubric()
        self.handleClick()

    def selectRubricByRow(self, rowNumber: int) -> None:
        self.RTW.currentWidget().selectRubricByRow(rowNumber)
        self.handleClick()

    def selectRubricByVisibleRow(self, rowNumber: int) -> None:
        self.RTW.currentWidget().selectRubricByVisibleRow(rowNumber)
        self.handleClick()

    def getCurrentTabName(self) -> str:
        return self.RTW.currentWidget().shortname

    def nextRubric(self) -> None:
        # change rubrics in the correct tab
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().nextRubric()
        else:
            self.tabHide.nextRubric()

    def previousRubric(self) -> None:
        # change rubrics in the correct tab
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().previousRubric()
        else:
            self.tabHide.previousRubric()

    def next_tab(self) -> None:
        """Move to next tab, only if tabs are shown."""
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            nt = (self.RTW.currentIndex() + 1) % numtabs
            self.RTW.setCurrentIndex(nt)
            # tab-change signal handles update - do not need 'handleClick' - called automatically

    def prev_tab(self) -> None:
        """Move to previous tab, only if tabs are shown."""
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            pt = (self.RTW.currentIndex() - 1) % numtabs
            self.RTW.setCurrentIndex(pt)
            # tab-change signal handles update - do not need 'handleClick' - called automatically

    def get_nonrubric_text_from_page(self) -> list[str]:
        """Find any text that isn't already part of a formal rubric.

        Returns:
            List of strings for each text on page that is not inside a rubric
        """
        return self._parent.get_nonrubric_text_from_page()

    def get_group_names(self) -> list[str]:
        """Return a list of strings consisting of the rubric group names."""
        groups = []
        for r in self.rubrics:
            tt = r["tags"]
            # TODO: share pack/unpack from tag w/ dialog & compute_score
            tt = tt.split()
            for t in tt:
                if t.startswith("group:"):
                    # TODO: Python >= 3.9, Issue #2887
                    # g = t.removeprefix("group:")
                    g = t[len("group:") :]
                    groups.append(g)
        return sorted(list(set(groups)))

    def unhide_rubric_by_rid(self, rid: int) -> None:
        wranglerState = self.get_tab_rubric_lists()
        try:
            wranglerState["hidden"].remove(rid)
        except ValueError:
            # TODO is this sufficient if we unexpectedly did not find it?
            log.warn(f"Tried to unhide {rid} but was already gone?  Or type mixup?")
            pass
        self.setRubricTabsFromState(wranglerState)

    def hide_rubric_by_rid(self, rid: int) -> None:
        wranglerState = self.get_tab_rubric_lists()
        wranglerState["hidden"].append(rid)
        self.setRubricTabsFromState(wranglerState)

    def add_new_rubric(self) -> None:
        """Open a dialog to create a new comment."""
        w = self.RTW.currentWidget()
        if w.is_group_tab():
            self._new_or_edit_rubric(None, add_to_group=w.shortname)
        else:
            self._new_or_edit_rubric(None)

    def other_usage(self, rid: int) -> None:
        """Open a dialog showing a list of tasks using the given rubric.

        Args:
            rid: the identifier of the rubric.
        """
        try:
            task_list = self._parent.getOtherRubricUsagesFromServer(rid)
        except PlomNoServerSupportException as e:
            WarnMsg(self, str(e)).exec()
            return
        (rubric,) = [r for r in self.rubrics if r["rid"] == rid]
        # dialog's parent is set to Annotator.
        RubricOtherUsageDialog(self._parent, task_list, rubric=rubric).exec()

    def view_other_paper(self, paper_number: int) -> None:
        """Opens another dialog to view a paper.

        Args:
            paper_number: the paper number of the paper to be viewed.
        """
        self._parent.view_other_paper(paper_number)

    def edit_rubric(self, key: int) -> None:
        """Open a dialog to edit a rubric - from the id-key of that rubric."""
        # first grab the rubric from that key
        try:
            index = [x["rid"] for x in self.rubrics].index(key)
        except ValueError:
            # no such rubric - this should not happen
            return
        com = self.rubrics[index]

        if com["username"] == self.username:
            self._new_or_edit_rubric(com, edit=True, index=index)
            return
        if com["system_rubric"]:
            msg = (
                "<p>This is a &ldquo;system rubric&rdquo; "
                "created by Plom itself; the server will probably not "
                "let you modify it.</p>"
            )
            edit_button = False
        elif self._parent.parentMarkerUI.msgr.is_legacy_server():
            # TODO: don't like "drilling up": maybe Annotator should know legacy or not
            msg = (
                "<p>You did not create this rubric "
                f"(it was created by &ldquo;{com['username']}&rdquo;).  "
                "You are connected to a legacy server which does not "
                " support modification of other user's rubrics.</p>"
            )
            edit_button = False
        else:
            # TODO: Displays username instead of preferred name, Issue #3048
            # TODO: would be nice if this dialog *knew* about the server settings
            msg = (
                "<p>You did not create this rubric "
                f"(it was created by &ldquo;{com['username']}&rdquo;).  "
                "Depending on server settings, you might not be allowed to "
                "modify it.</p>"
            )
            edit_button = True
        msgbox = SimpleQuestion(
            self, msg, "Do you want to make a copy and edit that instead?"
        )
        msgbox.setStandardButtons(QMessageBox.StandardButton.Cancel)
        msgbox.addButton("E&dit a copy", QMessageBox.ButtonRole.ActionRole)
        if edit_button:
            msgbox.addButton("Try to &edit anyway", QMessageBox.ButtonRole.ActionRole)
        msgbox.exec()
        clicked = msgbox.clickedButton()
        if not clicked:
            return
        if msgbox.buttonRole(clicked) == QMessageBox.ButtonRole.RejectRole:
            return
        if "copy" not in clicked.text().casefold():
            com = com.copy()
            # append a changelog of sorts to the meta field
            newmeta = [com["meta"]] if com["meta"] else []
            newmeta.append(f'Modified by "{self.username}"')
            com["meta"] = "\n".join(newmeta)
            self._new_or_edit_rubric(com, edit=True, index=index)
            return

        com = com.copy()  # don't muck-up the original
        newmeta = [com["meta"]] if com["meta"] else []
        newmeta.append(
            'Forked from Rubric ID {}, created by user "{}".'.format(
                com["rid"], com["username"]
            )
        )
        com["meta"] = "\n".join(newmeta)
        del com["rid"]
        com["username"] = self.username
        self._new_or_edit_rubric(com, edit=False)

    def _new_or_edit_rubric(
        self,
        com: dict[str, Any] | None,
        *,
        edit: bool = False,
        index: int | None = None,
        add_to_group: str | None = None,
    ) -> None:
        """Open a dialog to edit a comment or make a new one.

        Args:
            com (dict/None): a comment to modify or use as a template
                depending on next arg.  If set to None, which always
                means create new.

        Keyword Args:
            edit: True if we are modifying the comment.  If False, use
                `com` as a template for a new duplicated comment.
            index: the index of the comment inside the current rubric list
                used for updating the data in the rubric list after edit (only)
            add_to_group: if set to a string, the user might be trying to add
                to a group with this name.  For example, a UI could pre-select
                that option.  Mutually exclusive with `edit`, `index`, or
                at least ill-defined what happens if you pass those as well.

        Returns:
            None, does its work through side effects on the comment list.
        """
        reapable = self.get_nonrubric_text_from_page()
        arb = AddRubricBox(
            self,
            self.username,
            self.max_mark,
            self.question_index,
            self.question_label,
            self.version,
            self.max_version,
            com,
            groups=self.get_group_names(),
            reapable=reapable,
            experimental=self._parent.is_experimental(),
            add_to_group=add_to_group,
        )
        if arb.exec() != QDialog.DialogCode.Accepted:
            return
        new_rubric = arb.gimme_rubric_data()

        if edit:
            try:
                new_rubric = self._parent.modifyRubric(new_rubric["rid"], new_rubric)
            except PlomNoPermission as e:
                InfoMsg(self, f"No permission to modify that rubric: {e}").exec()
                return
            except PlomInconsistentRubric as e:
                ErrorMsg(self, f"Inconsistent Rubric: {e}").exec()
                return
            except PlomNoRubric as e:
                ErrorMsg(self, f"{e}").exec()
                return
            except PlomConflict as e:
                theirs = self._parent.getOneRubricFromServer(new_rubric["rid"])
                # ensure there is exactly one matching rubric in each list and grab it
                (old_rubric,) = [
                    r for r in self.rubrics if r["rid"] == new_rubric["rid"]
                ]
                RubricConflictDialog(
                    self, str(e), theirs, new_rubric, old_rubric
                ).exec()
                return

            # update the rubric in the current internal rubric list
            assert index is not None
            self.rubrics[index] = new_rubric
            # TODO: possibly a good time to do full refresh (?)

            # Debugging: change to True to slip in an unexpected change by another client
            # so that our *next* change will generate a conflict.
            if False and random.random() < 0.33:
                _tmp = new_rubric.copy()
                _tmp["text"] = _tmp["text"] + " [simulated offline comment change]"
                self._parent.modifyRubric(_tmp["rid"], _tmp)

        else:
            try:
                new_rubric = self._parent.createNewRubric(new_rubric)
            except PlomNoPermission as e:
                InfoMsg(self, f"No permission to create rubrics: {e}").exec()
                return
            self.rubrics.append(new_rubric)

        self.setRubricTabsFromState(self.get_tab_rubric_lists())

    def get_tab_rubric_lists(self) -> dict[str, list[Any]]:
        """Returns a dict of lists of the current rubrics."""
        return {
            "shown": self.tabS.get_rid_list(),
            "hidden": self.tabHide.get_rid_list(),
            "tab_order": [
                self.RTW.widget(n).shortname  # type: ignore[union-attr]
                for n in range(0, self.RTW.count())
            ],
            "user_tabs": [
                {"name": t.shortname, "ids": t.get_rid_list()}
                for t in self.get_user_tabs()
            ],
            "group_tabs": [
                {"name": t.shortname, "ids": t.get_rid_list()}
                for t in self.get_group_tabs()
            ],
        }
