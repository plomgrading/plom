# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Forest Kobayashi

import html
import logging
import re
from textwrap import shorten

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QPalette, QSyntaxHighlighter, QTextCharFormat

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QLabel,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QInputDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QToolButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from plom.misc_utils import next_in_longest_subsequence
from .useful_classes import InfoMsg, WarnMsg, SimpleQuestion
from .rubric_wrangler import RubricWrangler
from .rubrics import compute_score
from plom.plom_exceptions import PlomInconsistentRubric


log = logging.getLogger("annotr")


def rubric_is_naked_delta(r):
    if r["kind"] == "relative" and r["text"] == ".":
        return True
    return False


def isLegalRubric(rubric, *, scene, version, maxMark):
    """Checks the 'legality' of a particular rubric - returning one of several possible indicators

    Those states are:
    0 = incompatible - the kind of rubric is not compatible with the current state
    1 = compatible but out of range - the kind of rubric is compatible with the state but applying that rubric will take the score out of range [0, maxmark] (so cannot be used)
    2 = compatible and in range - is compatible and can be used.
    3 = version does not match - should be hidden by default.
    Note that the rubric lists use the result to decide which rubrics will
    be shown (2), hidden (0, 3) and greyed out (1)

    Args:
        rubric (dict):

    Keyword Args:
        scene (PageScene): we'll grab the in-use rubrics from it
        maxMark (int):
        version (int):

    Returns:
        int: 0, 1, 2, 3 as documented above.
    """
    if rubric["versions"]:
        if version not in rubric["versions"]:
            return 3

    if not scene:
        return 2

    rubrics = scene.get_rubrics()
    rubrics.append(rubric)

    try:
        _ = compute_score(rubrics, maxMark)
        return 2
    except ValueError:
        return 1
    except PlomInconsistentRubric:
        return 0


def render_params(template, params, ver):
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

    def __init__(self, parent, shortname=None, *, sort=False, tabType=None):
        """Initialize a new RubricTable.

        Args:
            parent:
            shortname (str):

        Keyword Args:
            tabType (str/None): "show", "hide", "group", "delta", `None`.
                Here `"show"` is used for the "All" tab, `None` is used
                for custom "user tabs".
            sort (bool):
        """
        super().__init__(parent)
        self._parent = parent
        self.tabType = tabType  # to help set menu
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        # Issue #1498: use these for shortcut key indicators
        self.verticalHeader().setVisible(False)
        self.setGridStyle(Qt.DotLine)
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
        # CSS cannot set relative fontsize
        f = self.font()
        f.setPointSizeF(0.67 * f.pointSizeF())
        self.verticalHeader().setFont(f)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        _col_headers = ("Key", "Username", "Delta", "Text")
        self.setColumnCount(len(_col_headers))
        self.setHorizontalHeaderLabels(_col_headers)
        self.hideColumn(0)
        self.hideColumn(1)
        # could use a subclass
        if self.tabType == "delta":
            self.hideColumn(3)
            # self.verticalHeader().setVisible(False)
        if sort:
            self.setSortingEnabled(True)
        self.shortname = shortname
        self.pressed.connect(self.handleClick)
        # self.itemChanged.connect(self.handleClick)
        self.doubleClicked.connect(self.editRow)

    def set_name(self, newname):
        if self.shortname != newname:
            log.debug("tab %s changing name to %s", self.shortname, newname)
        self.shortname = newname
        # TODO: assumes parent is TabWidget, can we do with signals/slots?
        # More like "If anybody cares, I just changed my name!"
        self._parent.update_tab_names()

    def is_user_tab(self):
        return self.tabType is None

    def is_group_tab(self):
        return self.tabType == "group"

    def is_delta_tab(self):
        return self.tabType == "delta"

    def is_hidden_tab(self):
        # TODO: naming here is confusing
        return self.tabType == "hide"

    def is_shared_tab(self):
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
        key = None if row is None else self.getKeyFromRow(row)

        # These are workaround for Issue #1441, lambdas in a loop
        def add_func_factory(t, k):
            def add_func():
                t.appendByKey(k)

            return add_func

        def del_func_factory(t, k):
            def del_func():
                t.removeRubricByKey(k)

            return del_func

        def edit_func_factory(t, k):
            def edit_func():
                t._parent.edit_rubric(k)

            return edit_func

        menu = QMenu(self)
        if key:
            a = QAction("Edit rubric", self)
            a.triggered.connect(edit_func_factory(self, key))
            menu.addAction(a)
            menu.addSeparator()

            for tab in self._parent.user_tabs:
                if tab == self:
                    continue
                a = QAction(f"Move to tab {tab.shortname}", self)
                a.triggered.connect(add_func_factory(tab, key))
                a.triggered.connect(del_func_factory(self, key))
                menu.addAction(a)
            menu.addSeparator()

            remAction = QAction("Remove from this tab", self)
            remAction.triggered.connect(del_func_factory(self, key))
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
        key = None if row is None else self.getKeyFromRow(row)

        # workaround for Issue #1441, lambdas in a loop
        def add_func_factory(t, k):
            def add_func():
                t.appendByKey(k)

            return add_func

        def edit_func_factory(t, k):
            def edit_func():
                t._parent.edit_rubric(k)

            return edit_func

        menu = QMenu(self)
        if key:
            a = QAction("Edit rubric", self)
            a.triggered.connect(edit_func_factory(self, key))
            menu.addAction(a)
            menu.addSeparator()

            # TODO: walk in another order for moveable tabs?
            # [self._parent.RTW.widget(n) for n in range(1, 5)]
            for tab in self._parent.user_tabs:
                a = QAction(f"Add to tab {tab.shortname}", self)
                a.triggered.connect(add_func_factory(tab, key))
                menu.addAction(a)
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

    def removeCurrentRubric(self):
        row = self.getCurrentRubricRow()
        if row is None:
            return
        self.removeRow(row)
        self.selectRubricByVisibleRow(0)
        self.handleClick()

    def removeRubricByKey(self, key):
        row = self.getRowFromKey(key)
        if row is None:
            return
        self.removeRow(row)
        self.selectRubricByVisibleRow(0)
        self.handleClick()

    def hideCurrentRubric(self):
        row = self.getCurrentRubricRow()
        if row is None:
            return
        key = self.item(row, 0).text()
        self._parent.hideRubricByKey(key)
        self.removeRow(row)
        self.selectRubricByVisibleRow(0)
        self.handleClick()

    def unhideCurrentRubric(self):
        row = self.getCurrentRubricRow()
        if row is None:
            return
        key = self.item(row, 0).text()
        self._parent.unhideRubricByKey(key)
        self.removeRow(row)
        self.selectRubricByVisibleRow(0)
        self.handleClick()

    def dropEvent(self, event):
        # fixed drop event using
        # https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget
        if event.source() == self:
            event.setDropAction(Qt.CopyAction)
            sourceRow = self.selectedIndexes()[0].row()
            targetRow = self.indexAt(event.pos()).row()
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

    def appendByKey(self, key):
        """Append the rubric associated with a key to the end of the list

        If its a dupe, don't add.

        args
            key (str/int?): the key associated with a rubric.

        raises
            what happens on invalid key?
        """
        # TODO: hmmm, should be dict?
        (rubric,) = [x for x in self._parent.rubrics if x["id"] == key]
        self.appendNewRubric(rubric)

    def appendNewRubric(self, rubric):
        rc = self.rowCount()
        # do sanity check for duplications
        for r in range(rc):
            if rubric["id"] == self.item(r, 0).text():
                return  # rubric already present
        # is a new rubric, so append it
        # Careful about sorting during setItem calls: Issue #2065
        _sorting_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.insertRow(rc)
        self.setItem(rc, 0, QTableWidgetItem(rubric["id"]))
        self.setItem(rc, 1, QTableWidgetItem(rubric["username"]))
        self.setItem(rc, 2, QTableWidgetItem(rubric["display_delta"]))

        # unfortunate parent access to get version
        render = render_params(
            rubric["text"], rubric["parameters"], self._parent.version
        )
        self.setItem(rc, 3, QTableWidgetItem(render))
        # set row header
        self.setVerticalHeaderItem(rc, QTableWidgetItem("{}".format(rc + 1)))
        self.colourLegalRubric(rc)
        # set a tooltip over delta that tells user the type of rubric
        self.item(rc, 2).setToolTip("{}-rubric".format(rubric["kind"]))
        # set a tooltip that contains tags and meta info when someone hovers over text
        hoverText = ""
        if rubric["tags"] != "":
            hoverText += "Tagged as {}\n".format(rubric["tags"])
        if rubric["meta"] != "":
            hoverText += "{}\n".format(rubric["meta"])
        self.item(rc, 3).setToolTip(hoverText.strip())
        self.setSortingEnabled(_sorting_enabled)

    def setRubricsByKeys(self, rubric_list, key_list):
        """Clear table and repopulate rubrics in the key_list"""
        # remove everything
        for r in range(self.rowCount()):
            self.removeRow(0)
        # since populating in order of key_list, build all keys from rubric_list
        rkl = [X["id"] for X in rubric_list]
        for id in key_list:
            try:  # guard against mysterious keys - should not happen unless people doing silliness
                rb = rubric_list[rkl.index(id)]
            except (ValueError, KeyError, IndexError):
                continue
            self.appendNewRubric(rb)

        self.resizeColumnsToContents()

    def setDeltaRubrics(self, rubrics, positive=True):
        """Clear table and repopulate with delta-rubrics"""
        # remove everything
        for r in range(self.rowCount()):
            self.removeRow(0)
        # grab the delta-rubrics from the rubricslist
        delta_rubrics = []
        for rb in rubrics:
            if rubric_is_naked_delta(rb):
                if (positive and int(rb["value"]) > 0) or (
                    not positive and int(rb["value"]) < 0
                ):
                    delta_rubrics.append(rb)

        # now sort in numerical order away from 0 and add
        for rb in sorted(delta_rubrics, key=lambda r: abs(int(r["value"]))):
            self.appendNewRubric(rb)
        # finally append the manager-created absolute rubrics
        for rb in rubrics:
            if rb["username"] == "manager" and rb["kind"] == "absolute":
                self.appendNewRubric(rb)

    def getKeyFromRow(self, row):
        return self.item(row, 0).text()

    def getKeyList(self):
        return [self.item(r, 0).text() for r in range(self.rowCount())]

    def getRowFromKey(self, key):
        for r in range(self.rowCount()):
            if int(self.item(r, 0).text()) == int(key):
                return r
        else:
            return None

    def getCurrentRubricRow(self):
        if not self.selectedIndexes():
            return None
        return self.selectedIndexes()[0].row()

    def getCurrentRubricKey(self):
        if not self.selectedIndexes():
            return None
        return self.item(self.selectedIndexes()[0].row(), 0).text()

    def reselectCurrentRubric(self):
        # If no selected row, then select row 0.
        # else select current row - triggers a signal.
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() == 0:
                return
            else:
                r = 0
        self.selectRubricByVisibleRow(r)

    def selectRubricByRow(self, r):
        """Select the r'th rubric in the list

        Args:
            r (int): The row-number in the rubric-table.
            If r is None, do nothing.
        """
        if r is not None:
            self.selectRow(r)

    def selectRubricByVisibleRow(self, r):
        """Select the r'th **visible** row

        Args:
            r (int): The row-number in the rubric-table.
            If r is None, do nothing.
        """
        rc = -1  # start here, so that correctly test after-increment
        for s in range(self.rowCount()):
            if not self.isRowHidden(s):
                rc += 1
            if rc == r:
                self.selectRow(s)
                return
        return

    def selectRubricByKey(self, key):
        """Select row with given key. Return true if works, else false"""
        if key is None:
            return False
        for r in range(self.rowCount()):
            if int(self.item(r, 0).text()) == int(key):
                self.selectRow(r)
                return True
        return False

    def nextRubric(self):
        """Move selection to the next row, wrapping around if needed."""
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() >= 1:
                self.selectRubricByVisibleRow(0)
                self.handleClick()  # actually force a click
            return
        rs = r  # get start row
        while True:  # move until we get back to start or hit unhidden row
            r = (r + 1) % self.rowCount()
            if r == rs or not self.isRowHidden(r):
                break
        self.selectRubricByRow(r)  # we know that row is not hidden
        self.handleClick()

    def previousRubric(self):
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

    def handleClick(self):
        # When an item is clicked, grab the details and emit rubric signal
        r = self.getCurrentRubricRow()
        if r is None:
            r = self.firstUnhiddenRow()
            if r is None:  # there is nothing unhidden here.
                return
            self.selectRubricByRow(r)

        rubric = self.selected_row_as_rubric(r).copy()
        # unfortunate parent access to get version
        rubric["text"] = render_params(
            rubric["text"], rubric["parameters"], self._parent.version
        )
        self._parent.rubricSignal.emit(rubric)

    def selected_row_as_rubric(self, r):
        id = self.item(r, 0).text()
        # TODO: we want a dict lookup
        for r in self._parent.rubrics:
            if r["id"] == id:
                return r

    def firstUnhiddenRow(self):
        for r in range(self.rowCount()):
            if not self.isRowHidden(r):
                return r
        return None

    def lastUnhiddenRow(self):
        for r in reversed(range(self.rowCount())):
            if not self.isRowHidden(r):
                return r
        return None

    def colourLegalRubric(self, r):
        legal = isLegalRubric(
            self.selected_row_as_rubric(r),
            scene=self._parent._parent.scene,
            version=self._parent.version,
            maxMark=self._parent.maxMark,
        )
        colour_legal = self.palette().color(QPalette.Active, QPalette.Text)
        colour_illegal = self.palette().color(QPalette.Disabled, QPalette.Text)
        # colour_hide = self.palette().color(QPalette.Disabled, QPalette.Text)
        if legal == 2:
            self.showRow(r)
            self.item(r, 2).setForeground(colour_legal)
            self.item(r, 3).setForeground(colour_legal)
        elif legal == 1:
            self.showRow(r)
            self.item(r, 2).setForeground(colour_illegal)
            self.item(r, 3).setForeground(colour_illegal)
        else:
            self.hideRow(r)
            # self.showRow(r)
            # self.item(r, 2).setForeground(colour_hide)
            # self.item(r, 3).setForeground(colour_hide)

    def updateLegality(self):
        """Style items according to their legality"""
        for r in range(self.rowCount()):
            self.colourLegalRubric(r)

    def editRow(self, tableIndex):
        r = tableIndex.row()
        rubricKey = self.item(r, 0).text()
        self._parent.edit_rubric(rubricKey)


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

    def __init__(self):
        super().__init__()

    def mousePressEvent(self, mouseEvent):
        if mouseEvent.button() == Qt.RightButton:
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


class RubricWidget(QWidget):
    """The RubricWidget is a multi-tab interface for displaying, choosing and managing rubrics."""

    # This is picked up by the annotator to tell the scene the current rubric
    rubricSignal = pyqtSignal(dict)

    def __init__(self, parent):
        super().__init__(parent)
        self.question_label = None
        self.question_number = None
        self.version = None
        self.max_version = None
        self._parent = parent
        self.username = parent.username
        self.rubrics = []
        self.maxMark = None

        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        deltaP_label = "+\N{Greek Small Letter Delta}"
        deltaN_label = "\N{Minus Sign}\N{Greek Small Letter Delta}"
        self.tabS = RubricTable(self, shortname="All", tabType="show")
        self.tabDeltaP = RubricTable(self, shortname=deltaP_label, tabType="delta")
        self.tabDeltaN = RubricTable(self, shortname=deltaN_label, tabType="delta")
        self.RTW = QTabWidget()
        tb = TabBarWithAddRenameRemoveContext()
        # TODO: is this normal or should one connect the signals in the ctor?
        tb.add_tab_signal.connect(self.add_new_tab)
        tb.rename_tab_signal.connect(self.rename_tab)
        tb.remove_tab_signal.connect(self.remove_tab)
        self.RTW.setTabBar(tb)
        self.RTW.setMovable(True)
        self.RTW.tabBar().setChangeCurrentOnDrag(True)
        self.RTW.insertTab(0, self.tabS, self.tabS.shortname)
        self.RTW.insertTab(1, self.tabDeltaP, self.tabDeltaP.shortname)
        self.RTW.insertTab(2, self.tabDeltaN, self.tabDeltaN.shortname)
        self.RTW.tabBar().setTabData(0, self.tabS.tabType)
        self.RTW.tabBar().setTabData(1, self.tabDeltaP.tabType)
        self.RTW.tabBar().setTabData(2, self.tabDeltaN.tabType)
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
        b.setPopupMode(QToolButton.InstantPopup)
        self.RTW.setCornerWidget(b)
        self.RTW.setCurrentIndex(0)  # start on shared tab
        # connect the 'tab-change'-signal to 'handleClick' to fix #1497
        self.RTW.currentChanged.connect(self.handleClick)

        self.tabHide = RubricTable(self, sort=True, tabType="hide")
        self.groupHide = QTabWidget()
        self.groupHide.addTab(self.tabHide, "Hidden")
        self.showHideW = QStackedWidget()
        self.showHideW.addWidget(self.RTW)
        self.showHideW.addWidget(self.groupHide)
        grid.addWidget(self.showHideW, 1, 1, 2, 4)
        self.addB = QPushButton("&Add")  # faster debugging, could remove?
        self.filtB = QPushButton("Arrange/Filter")
        self.hideB = QPushButton("Shown/Hidden")
        self.syncB = QToolButton()
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

    def toggleShowHide(self):
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

    def get_user_tabs(self):
        """Get an ordered list of user-defined tabs."""
        # this is all tabs: we want only the user ones
        # return [self.RTW.widget(n) for n in range(self.RTW.count())]
        L = []
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            if tab.is_user_tab():
                L.append(tab)
        return L

    def get_group_tabs(self):
        """Get an ordered list of the group tabs."""
        L = []
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            if tab.is_group_tab():
                L.append(tab)
        return L

    def get_group_tabs_dict(self):
        """Get a dict of the group tabs, keyed by name"""
        d = {}
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            if tab.is_group_tab():
                d[tab.shortname] = tab
        return d

    def update_tab_names(self):
        """Loop over the tabs and update their displayed names"""
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            self.RTW.setTabText(n, tab.shortname)
            # colours that seem vaguely visible in both light/dark theme: "teal", "olive"
            if tab.is_user_tab():
                self.RTW.setTabToolTip(n, "custom tab")
                # TODO: blend green with palette color?
                self.RTW.tabBar().setTabTextColor(n, QColor("teal"))
            elif tab.is_group_tab():
                self.RTW.setTabToolTip(n, "shared group")
                # maybe no need to highlight shared tabs?
                # self.RTW.tabBar().setTabTextColor(n, QColor("olive"))
            # elif tab.is_shared_tab():
            #     self.RTW.setTabToolTip(n, "All rubrics")
            # elif tab.is_delta_tab():
            #     self.RTW.setTabToolTip(n, "delta")

    def add_new_group_tab(self, name):
        """Add new group-defined tab

        The new tab is inserted after the right-most "group" tab, or
        immediately after the "All" tab if there are no "group" tabs.

        args:
            name (str): name of the new tab.

        return:
            RubricTable: the newly added table.
        """
        tab = RubricTable(self, shortname=name, tabType="group")
        idx = None
        for n in range(0, self.RTW.count()):
            if self.RTW.widget(n).is_group_tab():
                idx = n
        if idx is None:
            idx = 0
        # insert tab after that
        self.RTW.insertTab(idx + 1, tab, tab.shortname)
        self.RTW.tabBar().setTabData(idx + 1, tab.tabType)
        self.update_tab_names()
        return tab

    def add_new_tab(self, name=None):
        """Add new user-defined tab either to end or near end.

        The new tab is inserted after the right-most non-delta tab.
        For example, the default config has delta tabs at the end; if
        user adds a new tab, it appears before these.  But the user may
        have rearranged the delta tabs left of their custom tabs.

        args:
            name (str/None): name of the new tab.  If omitted or None,
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
                if msg.exec() == QMessageBox.No:
                    return

        if not name:
            tab_names = [x.shortname for x in self.get_user_tabs()]
            name = next_in_longest_subsequence(tab_names)
        if not name:
            syms = (
                "\N{Black Star}",
                "\N{Black Heart Suit}",
                "\N{Black Spade Suit}",
                "\N{Black Diamond Suit}",
                "\N{Black Club Suit}",
                "\N{Double Dagger}",
                "\N{Floral Heart}",
                "\N{Rotated Floral Heart Bullet}",
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
        while self.RTW.widget(n).is_delta_tab() and n > 0:  # small sanity check
            n = n - 1
        # insert tab after it
        self.RTW.insertTab(n + 1, tab, tab.shortname)
        self.RTW.tabBar().setTabData(n + 1, tab.tabType)
        self.update_tab_names()

    def remove_current_tab(self):
        n = self.RTW.currentIndex()
        self.remove_tab(n)

    def remove_tab(self, n):
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
        if SimpleQuestion(self, msg).exec() == QMessageBox.No:
            return
        self.RTW.removeTab(n)
        tab.clear()
        tab.deleteLater()

    def rename_current_tab(self):
        n = self.RTW.currentIndex()
        self.rename_tab(n)

    def rename_tab(self, n):
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
                if s == self.RTW.widget(n).shortname:
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

    def refreshRubrics(self):
        """Get rubrics from server and if non-trivial then repopulate"""
        old_rubrics = self.rubrics
        self.rubrics = self._parent.getRubricsFromServer()
        self.setRubricTabsFromState(self.get_tab_rubric_lists())
        self._parent.saveTabStateToServer(self.get_tab_rubric_lists())
        msg = "<p>\N{Check Mark} Your tabs have been synced to the server.</p>\n"
        diff = set(d["id"] for d in self.rubrics) - set(d["id"] for d in old_rubrics)
        if not diff:
            msg += "<p>\N{Check Mark} No new rubrics are available.</p>\n"
        else:
            msg += f"<p>\N{Check Mark} <b>{len(diff)} new rubrics</b> have been downloaded from the server:</p>\n"
            diff = [r for r in self.rubrics for i in diff if r["id"] == i]
            ell = "\N{HORIZONTAL ELLIPSIS}"
            abbrev = []
            # We truncate the list to this many
            display_at_most = 12
            for n, r in enumerate(diff):
                delta = ".&nbsp;" if r["display_delta"] == "." else r["display_delta"]
                text = html.escape(shorten(r["text"], 36, placeholder=ell))
                render = f"<li><tt>{delta}</tt> <i>&ldquo;{text}&rdquo;</i>&nbsp; by {r['username']}</li>"
                if n < (display_at_most - 1):
                    abbrev.append(render)
                elif n == (display_at_most - 1) and len(diff) == display_at_most:
                    # include the last one if it fits...
                    abbrev.append(render)
                elif n == (display_at_most - 1):
                    # otherwise ellipsize the remainder
                    abbrev.append("<li>" + "&nbsp;" * 6 + "\N{VERTICAL ELLIPSIS}</li>")
                    break
            msg += '<ul style="list-style-type:none;">\n  {}\n</ul>'.format(
                "\n  ".join(abbrev)
            )
        QMessageBox(
            QMessageBox.Information,
            "Finished syncing rubrics",
            msg,
            QMessageBox.Ok,
            self,
        ).exec()
        # TODO: could add a "Open Rubric Wrangler" button to above dialog?
        # self.wrangleRubricsInteractively()
        # TODO: if adding that, it should push tabs *again* on accept but not on cancel
        self.updateLegalityOfRubrics()

    def wrangleRubricsInteractively(self):
        wr = RubricWrangler(
            self,
            self.rubrics,
            self.get_tab_rubric_lists(),
            self.username,
            annotator_size=self._parent.size(),
        )
        if wr.exec() != QDialog.Accepted:
            return
        else:
            self.setRubricTabsFromState(wr.wranglerState)

    def setInitialRubrics(self, user_tab_state=None):
        """Grab rubrics from server and set sensible initial values.

        Note: must be called after annotator knows its tgv etc, so
        maybe difficult to call from __init__.  TODO: a possible
        refactor would have the caller (which is probably `_parent`)
        get the server rubrics list and pass in as an argument.

        args:
            wranglerState (dict/None): a representation of the state of
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

    def setRubricTabsFromState(self, wranglerState=None):
        """Set rubric tabs (but not rubrics themselves) from saved data.

        The various rubric tabs are updated based on data passed in.
        The rubrics themselves are uneffected.

        args:
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
                rubric["id"] not in wranglerState["hidden"]
                and rubric["id"] not in wranglerState["shown"]
            ):
                log.info("Appending new rubric with id {}".format(rubric["id"]))
                wranglerState["shown"].append(rubric["id"])

        group_tab_data = {}
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
                group_tab_data[g].append(rubric["id"])

        # TODO: order of rubrics within group tabs?
        current_group_tabs = self.get_group_tabs_dict()
        for name, tab in current_group_tabs.items():
            if name not in group_tab_data.keys():
                log.info("Removing now-empty tab: group %s is now empty", name)
                self.RTW.removeTab(self.RTW.indexOf(tab))
        for g in sorted(group_tab_data.keys()):
            idlist = group_tab_data[g]
            tab = current_group_tabs.get(g)
            if tab is None:
                tab = self.add_new_group_tab(g)
            tab.setRubricsByKeys(self.rubrics, idlist)

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
                log.warn("renaming user tab %s to %s for conflict", name, name + "'")
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
            tab.setRubricsByKeys(self.rubrics, idlist)
        self.tabS.setRubricsByKeys(self.rubrics, wranglerState["shown"])
        self.tabDeltaP.setDeltaRubrics(self.rubrics, positive=True)
        self.tabDeltaN.setDeltaRubrics(self.rubrics, positive=False)
        self.tabHide.setRubricsByKeys(self.rubrics, wranglerState["hidden"])

        try:
            self.reorder_tabs(wranglerState["tab_order"])
        except AssertionError as e:
            # its not critical to re-order: if it fails just log
            log.error("Unexpected failure sorting tabs: %s", str(e))

        self.update_tab_names()

        # make sure something selected in each tab
        self.tabHide.selectRubricByVisibleRow(0)
        self.tabDeltaP.selectRubricByVisibleRow(0)
        self.tabDeltaN.selectRubricByVisibleRow(0)
        self.tabS.selectRubricByVisibleRow(0)
        for tab in self.user_tabs:
            tab.selectRubricByVisibleRow(0)

    def reorder_tabs(self, target_order):
        """Change the order of the tabs to match a target order.

        args:
            target_order (list): a list of strings for the order we would
                like to see.  We will copy and then dedupe this input.

        returns:
            None: but modifies the tab order.

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
        current = [self.RTW.widget(n).shortname for n in range(0, self.RTW.count())]
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
            current = [self.RTW.widget(n).shortname for n in range(0, self.RTW.count())]
            # print((i, current))
            # we know we can find it b/c we just updated target
            j = target_order.index(current[i])
            if i == j:
                # all indices before this are now in the correct order
                i += 1
                continue
            self.RTW.tabBar().moveTab(i, j)
        check = [self.RTW.widget(n).shortname for n in range(0, self.RTW.count())]
        assert check == target_order, "did not achieve target"

    def getCurrentRubricKeyAndTab(self):
        """return the current rubric key and the current tab.

        returns:
            list: [a,b] where a=rubric-key=(int/none) and b=current tab index = int
        """
        return [
            self.RTW.currentWidget().getCurrentRubricKey(),
            self.RTW.currentIndex(),
        ]

    def setCurrentRubricKeyAndTab(self, key, tab):
        """set the current rubric key and the current tab

        args
            key (int/None): which rubric to highlight.  If no None, no action.
            tab (int): which tab to choose.

        returns:
            bool: True if we set a row, False if we could not find an appropriate row
                b/c for example key or tab are invalid or not found.
        """
        if key is None:
            return False
        if tab in range(0, self.RTW.count()):
            self.RTW.setCurrentIndex(tab)
        else:
            return False
        return self.RTW.currentWidget().selectRubricByKey(key)

    def setQuestion(self, num, label):
        """Set relevant question number and label.

        args:
            num (int/None): the question number.
            label (str/None): the question label.

        After calling this, you should call updateLegalityOfRubrics() to
        update which rubrics are highlighted/displayed.
        """
        self.question_number = num
        self.question_label = label

    def setVersion(self, version, maxver):
        """Set version being graded.

        args:
            version (int/None): which version.
            maxver (int): the largest version in this assessment.

        After calling this, you should call updateLegalityOfRubrics() to
        update which rubrics are highlighted/displayed.
        """
        self.version = version
        self.max_version = maxver

    def setMaxMark(self, maxMark):
        """Update the max mark.

        args:
            maxMark (int):

        After calling this, you should call updateLegalityOfRubrics() to
        update which rubrics are highlighted/displayed.
        """
        self.maxMark = maxMark

    def updateLegalityOfRubrics(self):
        """Redo the colour highlight/deemphasis in each tab"""
        self.tabS.updateLegality()
        for tab in self.get_user_tabs():
            tab.updateLegality()
        for tab in self.get_group_tabs():
            tab.updateLegality()
        self.tabDeltaP.updateLegality()
        self.tabDeltaN.updateLegality()

    def handleClick(self):
        self.RTW.currentWidget().handleClick()

    def reselectCurrentRubric(self):
        self.RTW.currentWidget().reselectCurrentRubric()
        self.handleClick()

    def selectRubricByRow(self, rowNumber):
        self.RTW.currentWidget().selectRubricByRow(rowNumber)
        self.handleClick()

    def selectRubricByVisibleRow(self, rowNumber):
        self.RTW.currentWidget().selectRubricByVisibleRow(rowNumber)
        self.handleClick()

    def getCurrentTabName(self):
        return self.RTW.currentWidget().shortname

    def nextRubric(self):
        # change rubrics in the correct tab
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().nextRubric()
        else:
            self.tabHide.nextRubric()

    def previousRubric(self):
        # change rubrics in the correct tab
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().previousRubric()
        else:
            self.tabHide.previousRubric()

    def next_tab(self):
        """Move to next tab, only if tabs are shown."""
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            nt = (self.RTW.currentIndex() + 1) % numtabs
            self.RTW.setCurrentIndex(nt)
            # tab-change signal handles update - do not need 'handleClick' - called automatically

    def prev_tab(self):
        """Move to previous tab, only if tabs are shown."""
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            pt = (self.RTW.currentIndex() - 1) % numtabs
            self.RTW.setCurrentIndex(pt)
            # tab-change signal handles update - do not need 'handleClick' - called automatically

    def get_nonrubric_text_from_page(self):
        """Find any text that isn't already part of a formal rubric.

        Returns:
            list: strings for each text on page that is not inside a rubric
        """
        return self._parent.get_nonrubric_text_from_page()

    def get_group_names(self):
        groups = []
        for r in self.rubrics:
            tt = r["tags"]
            # TODO: share pack/unpack from tag w/ dialog & compute_score
            tt = tt.split()
            for t in tt:
                if t.startswith("group:"):
                    # TODO: Python >= 3.9
                    # g = t.removeprefix("group:")
                    g = t[len("group:") :]
                    groups.append(g)
        return sorted(list(set(groups)))

    def unhideRubricByKey(self, key):
        index = [x["id"] for x in self.rubrics].index(key)
        self.tabS.appendNewRubric(self.rubrics[index])

    def hideRubricByKey(self, key):
        index = [x["id"] for x in self.rubrics].index(key)
        self.tabHide.appendNewRubric(self.rubrics[index])

    def add_new_rubric(self):
        """Open a dialog to create a new comment."""
        self._new_or_edit_rubric(None)

    def edit_rubric(self, key):
        """Open a dialog to edit a rubric - from the id-key of that rubric."""
        # first grab the rubric from that key
        try:
            index = [x["id"] for x in self.rubrics].index(key)
        except ValueError:
            # no such rubric - this should not happen
            return
        com = self.rubrics[index]

        if com["username"] == self.username:
            self._new_or_edit_rubric(com, edit=True, index=index)
            return
        msg = SimpleQuestion(
            self,
            "<p>You did not create this rubric "
            f"(it was created by &ldquo;{com['username']}&rdquo;).</p>",
            "Do you want to make a copy and edit that instead?",
        )
        if msg.exec() == QMessageBox.No:
            return
        com = com.copy()  # don't muck-up the original
        newmeta = [com["meta"]] if com["meta"] else []
        newmeta.append(
            'Forked from Rubric ID {}, created by user "{}".'.format(
                com["id"], com["username"]
            )
        )
        com["meta"] = "\n".join(newmeta)
        com["id"] = None
        com["username"] = self.username
        self._new_or_edit_rubric(com, edit=False)

    def _new_or_edit_rubric(self, com, edit=False, index=None):
        """Open a dialog to edit a comment or make a new one.

        args:
            com (dict/None): a comment to modify or use as a template
                depending on next arg.  If set to None, which always
                means create new.
            edit (bool): are we modifying the comment?  if False, use
                `com` as a template for a new duplicated comment.
            index (int): the index of the comment inside the current rubric list
                used for updating the data in the rubric list after edit (only)

        Returns:
            None: does its work through side effects on the comment list.
        """
        if self.question_number is None:
            log.error("Not allowed to create rubric while question number undefined.")
            return
        reapable = self.get_nonrubric_text_from_page()
        arb = AddRubricBox(
            self,
            self.username,
            self.maxMark,
            self.question_number,
            self.question_label,
            self.version,
            self.max_version,
            reapable,
            com,
            annotator_size=self._parent.size(),
            groups=self.get_group_names(),
            experimental=self._parent.is_experimental(),
        )
        if arb.exec() != QDialog.Accepted:  # ARB does some simple validation
            return
        new_rubric = arb.gimme_rubric_data()

        if edit:
            key = self._parent.modifyRubric(new_rubric["id"], new_rubric)
            # update the rubric in the current internal rubric list
            # make sure that keys match.
            assert key == new_rubric["id"]
            assert self.rubrics[index]["id"] == new_rubric["id"]
            # then replace
            self.rubrics[index] = new_rubric
        else:
            new_rubric.pop("id")
            new_rubric["id"] = self._parent.createNewRubric(new_rubric)
            # at this point we have an accepted new rubric
            # add it to the internal list of rubrics
            self.rubrics.append(new_rubric)

        self.setRubricTabsFromState(self.get_tab_rubric_lists())
        # finally - select that rubric and simulate a click
        self.RTW.currentWidget().selectRubricByKey(new_rubric["id"])
        self.handleClick()

    def get_tab_rubric_lists(self):
        """returns a dict of lists of the current rubrics.

        Currently does not include "group tabs".
        """
        return {
            "shown": self.tabS.getKeyList(),
            "hidden": self.tabHide.getKeyList(),
            "tab_order": [
                self.RTW.widget(n).shortname for n in range(0, self.RTW.count())
            ],
            "user_tabs": [
                {"name": t.shortname, "ids": t.getKeyList()} for t in self.user_tabs
            ],
        }


class SignedSB(QSpinBox):
    # add an explicit sign to spinbox and no 0
    # range is from -N,..,-1,1,...N
    # note - to fix #1561 include +/- N in this range.
    # else 1 point questions become very problematic
    def __init__(self, maxMark):
        super().__init__()
        self.setRange(-maxMark, maxMark)
        self.setValue(1)

    def stepBy(self, steps):
        self.setValue(self.value() + steps)
        # to skip 0.
        if self.value() == 0:
            self.setValue(self.value() + steps)

    def textFromValue(self, n):
        t = QSpinBox().textFromValue(n)
        if n > 0:
            return "+" + t
        else:
            return t


class SubstitutionsHighlighter(QSyntaxHighlighter):
    """Highlight tex prefix and parametric substitutions."""

    def __init__(self, *args, **kwargs):
        # TODO: initial value of subs?
        self.subs = []
        super().__init__(*args, **kwargs)

    def highlightBlock(self, txt):
        """Highlight tex prefix and matches in our substitution list.

        args:
            txt (str): the text to be highlighted.

        TODO: use colours from the palette?
        """
        # TODO: can we set a popup: "v2 value: 'x'"
        # reset format
        self.setFormat(0, len(txt), QTextCharFormat())
        # highlight tex: at beginning
        if txt.startswith("tex:"):  # casefold?
            self.setFormat(0, len("tex:"), QColor("grey"))
        # highlight parametric substitutions
        for s in self.subs:
            for match in re.finditer(s, txt):
                # print(f"matched on {s} at {match.start()} to {match.end()}!")
                frmt = QTextCharFormat()
                frmt.setForeground(QColor("teal"))
                # TODO: not sure why this doesn't work?x
                frmt.setToolTip('v2 subs: "meh"')
                self.setFormat(match.start(), match.end() - match.start(), frmt)

    def setSubs(self, subs):
        self.subs = subs
        self.rehighlight()


class AddRubricBox(QDialog):
    def __init__(
        self,
        parent,
        username,
        maxMark,
        question_number,
        question_label,
        version,
        maxver,
        reapable,
        com=None,
        *,
        annotator_size=None,
        groups=[],
        experimental=False,
    ):
        """Initialize a new dialog to edit/create a comment.

        Args:
            parent (QWidget): the parent window.
            username (str)
            maxMark (int)
            question_number (int)
            question_label (str)
            version (int)
            maxver (int)
            reapable (list): these are used to "harvest" plain 'ol text
                annotations and morph them into comments.
            com (dict/None): if None, we're creating a new rubric.
                Otherwise, this has the current comment data.

        Keyword Args:
            annotator_size (QSize/None): size of the parent annotator
            groups (list): existing group names that the rubric could be
                added to.
            experimental (bool): whether to enable experimental or advanced
                features.
        """
        super().__init__(parent)

        self.use_experimental_features = experimental
        self.question_number = question_number
        self.version = version
        self.maxver = maxver

        if com:
            self.setWindowTitle("Modify rubric")
        else:
            self.setWindowTitle("Add new rubric")

        # Set self to be 1/2 the size of the annotator
        if annotator_size:
            self.resize(annotator_size / 2)

        self.reapable_CB = QComboBox()
        self.TE = QTextEdit()
        self.hiliter = SubstitutionsHighlighter(self.TE)
        self.SB = SignedSB(maxMark)
        self.TEtag = QLineEdit()
        self.TEmeta = QTextEdit()
        # cannot edit these
        self.label_rubric_id = QLabel("Will be auto-assigned")
        self.Luser = QLabel()

        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        sizePolicy.setVerticalStretch(3)

        #
        self.TE.setSizePolicy(sizePolicy)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(1)
        self.TEmeta.setSizePolicy(sizePolicy)
        # TODO: make everything wider!

        flay = QFormLayout()
        flay.addRow("Text", self.TE)
        lay = QHBoxLayout()
        lay.addItem(
            QSpacerItem(32, 10, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        )
        lay.addWidget(QLabel("Choose text from page:"))
        lay.addWidget(self.reapable_CB)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.reapable_CB.setSizePolicy(sizePolicy)
        flay.addRow("", lay)

        frame = QFrame()
        vlay = QVBoxLayout(frame)
        vlay.setContentsMargins(0, 0, 0, 0)
        b = QRadioButton("neutral")
        b.setToolTip("more of a comment, this rubric does not change the mark")
        b.setChecked(True)
        vlay.addWidget(b)
        self.typeRB_neutral = b
        lay = QHBoxLayout()
        b = QRadioButton("relative")
        b.setToolTip("changes the mark up or down by some number of points")
        lay.addWidget(b)
        self.typeRB_relative = b
        # lay.addWidget(self.DE)
        lay.addWidget(self.SB)
        self.SB.textChanged.connect(b.click)
        # self.SB.clicked.connect(b.click)
        lay.addItem(QSpacerItem(16, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
        lay.addItem(QSpacerItem(48, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        vlay.addLayout(lay)
        hlay = QHBoxLayout()
        b = QRadioButton("absolute")
        abs_tooltip = "Indicates a score as a part of a maximum possible amount"
        b.setToolTip(abs_tooltip)
        hlay.addWidget(b)
        self.typeRB_absolute = b
        _ = QSpinBox()
        _.setRange(0, maxMark)
        _.setValue(0)
        _.textChanged.connect(b.click)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        self.rubric_value_SB = _
        _ = QLabel("out of")
        _.setToolTip(abs_tooltip)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        _ = QSpinBox()
        _.setRange(0, maxMark)
        _.setValue(maxMark)
        _.textChanged.connect(b.click)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        self.rubric_out_of_SB = _
        # TODO: remove this notice
        hlay.addWidget(QLabel("  (experimental!)"))
        if not self.use_experimental_features:
            self.typeRB_absolute.setEnabled(False)
        hlay.addItem(QSpacerItem(48, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        vlay.addLayout(hlay)
        flay.addRow("Marks", frame)

        # scope
        self.scopeButton = QToolButton()
        self.scopeButton.setCheckable(True)
        self.scopeButton.setChecked(False)
        self.scopeButton.setAutoRaise(True)
        self.scopeButton.setText("Scope")
        self.scopeButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.scopeButton.clicked.connect(self.toggle_scope_elements)
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        self.scope_frame = frame
        flay.addRow(self.scopeButton, frame)
        vlay = QVBoxLayout(frame)
        cb = QCheckBox(
            f'specific to question "{question_label}" (index {question_number})'
        )
        cb.setEnabled(False)
        cb.setChecked(True)
        vlay.addWidget(cb)
        # For the future, once implemented:
        # label = QLabel("Specify a list of question indices to share this rubric.")
        # label.setWordWrap(True)
        # vlay.addWidget(label)
        vlay.addWidget(QLabel("<hr>"))
        lay = QHBoxLayout()
        cb = QCheckBox("specific to version(s)")
        cb.stateChanged.connect(self.toggle_version_specific)
        lay.addWidget(cb)
        self.version_specific_cb = cb
        le = QLineEdit()
        lay.addWidget(le)
        self.version_specific_le = le
        space = QSpacerItem(48, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.version_specific_space = space
        lay.addItem(space)
        vlay.addLayout(lay)
        if maxver > 1:
            # TODO: coming soon notice and setEnabled(False) below
            s = "<p>By default, rubrics are shared between versions of a question.<br />"
            s += " Experimental feature: You can also parameterize this rubric by"
            s += " making version-specific substitutions.</p>"
        else:
            s = "<p>By default, rubrics are shared between versions of a question.</p>"
        label = QLabel(s)
        label.setWordWrap(True)
        # label.setAlignment(Qt.AlignTop)
        # Note: I often have problems with wordwrapped QLabels taking
        # too much space, seems putting inside a QFrame fixed that!
        vlay.addWidget(label)
        self._param_grid = QGridLayout()  # placeholder
        vlay.addLayout(self._param_grid)
        vlay.addWidget(QLabel("<hr>"))
        hlay = QHBoxLayout()
        self.group_checkbox = QCheckBox("Associate with the group ")
        hlay.addWidget(self.group_checkbox)
        b = QComboBox()
        # b.setEditable(True)
        # b.setDuplicatesEnabled(False)
        b.addItems(groups)
        # changing the group ticks the group checkbox
        b.activated.connect(lambda: self.group_checkbox.setChecked(True))
        hlay.addWidget(b)
        self.group_combobox = b
        b = QToolButton(text="➕")
        b.setToolTip("Add new group")
        b.setAutoRaise(True)
        b.clicked.connect(self.add_new_group)
        self.group_add_btn = b
        hlay.addWidget(b)
        # b = QToolButton(text="➖")
        # b.setToolTip("Delete currently-selected group")
        # b.setAutoRaise(True)
        # hlay.addWidget(b)
        hlay.addItem(QSpacerItem(48, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        b = QToolButton(text="What are groups?")
        b.setAutoRaise(True)
        msg = """<p>Groups are intended for multi-part questions.
              For example, you could make groups &ldquo;(a)&rdquo;,
              &ldquo;(b)&rdquo; and &ldquo;(c)&rdquo;.
              Some tips:</p>
            <ul>
            <li><b>This is an experimental feature:</b> please discuss
              with your team.</li>
            <li>Groups create automatic tabs, shared with other users.
              <b>Other users may need to click the &ldquo;sync&rdquo; button.</b>
            </li>
            <li>Making a rubric <em>exclusive</em> means it cannot be used alongside
              others from the same exclusion group.</li>
            <li>Groups will disappear if no rubrics are in them.</li>
            <ul>
        """
        b.clicked.connect(lambda: InfoMsg(self, msg).exec())
        hlay.addWidget(b)
        vlay.addLayout(hlay)
        hlay = QHBoxLayout()
        hlay.addItem(QSpacerItem(24, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
        # TODO: note default for absolute rubrics?  (once it is the default)
        c = QCheckBox("Exclusive in this group (at most one such rubric can be placed)")
        hlay.addWidget(c)
        self.group_excl = c
        self.group_checkbox.toggled.connect(lambda x: self.group_excl.setEnabled(x))
        self.group_checkbox.toggled.connect(lambda x: self.group_combobox.setEnabled(x))
        self.group_checkbox.toggled.connect(lambda x: self.group_add_btn.setEnabled(x))
        # TODO: connect self.typeRB_neutral etc change to check/uncheck the exclusive button
        self.group_excl.setChecked(False)
        self.group_excl.setEnabled(False)
        self.group_combobox.setEnabled(False)
        self.group_add_btn.setEnabled(False)
        self.group_checkbox.setChecked(False)
        vlay.addLayout(hlay)
        self.toggle_version_specific()
        self.toggle_scope_elements()

        # TODO: in the future?
        flay.addRow("Tags", self.TEtag)
        self.TEtag.setEnabled(False)
        flay.addRow("Meta", self.TEmeta)

        flay.addRow("Rubric ID", self.label_rubric_id)
        flay.addRow("Created by", self.Luser)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        # set up widgets
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        if reapable:
            self.reapable_CB.addItem("")
            self.reapable_CB.addItems(reapable)
        else:
            self.reapable_CB.setEnabled(False)
        # Set up TE and CB so that when CB changed, text is updated
        self.reapable_CB.currentTextChanged.connect(self.changedReapableCB)

        params = []
        # If supplied with current text/delta then set them
        if com:
            if com["text"]:
                self.TE.clear()
                self.TE.insertPlainText(com["text"])
            if com["meta"]:
                self.TEmeta.clear()
                self.TEmeta.insertPlainText(com["meta"])
            if com["kind"]:
                if com["kind"] == "neutral":
                    self.typeRB_neutral.setChecked(True)
                elif com["kind"] == "relative":
                    self.SB.setValue(int(com["value"]))
                    self.typeRB_relative.setChecked(True)
                elif com["kind"] == "absolute":
                    self.rubric_value_SB.setValue(int(com["value"]))
                    self.rubric_out_of_SB.setValue(int(com["out_of"]))
                    self.typeRB_absolute.setChecked(True)
                else:
                    raise RuntimeError(f"unexpected kind in {com}")
            if com["id"]:
                self.label_rubric_id.setText(str(com["id"]))
            if com["username"]:
                self.Luser.setText(com["username"])
            if com["versions"]:
                self.version_specific_cb.setChecked(True)
                self.version_specific_le.setText(
                    ", ".join(str(x) for x in com["versions"])
                )
            if com["parameters"]:
                params = com["parameters"]
            tags = com.get("tags", "").split()
            # TODO: Python >= 3.9: t.removeprefix("exclusive:")
            exclusives = [
                t[len("exclusive:") :] for t in tags if t.startswith("exclusive:")
            ]
            groups = [t[len("group:") :] for t in tags if t.startswith("group:")]

            if not groups and not exclusives:
                pass
            elif len(groups) == 1:
                (g,) = groups
                self.group_combobox.setCurrentText(g)
                self.group_checkbox.setChecked(True)
                if not exclusives:
                    self.group_excl.setChecked(False)
                    tags.remove(f"group:{g}")
                elif len(exclusives) == 1 and exclusives[0] == g:
                    self.group_excl.setChecked(True)
                    tags.remove(f"exclusive:{exclusives[0]}")
                    tags.remove(f"group:{g}")
                else:
                    # not UI representable: disable UI controls
                    self.group_checkbox.setEnabled(False)
                    self.group_excl.setEnabled(False)
                    self.TEtag.setEnabled(True)
            else:
                # not UI representable: disable UI controls
                self.group_checkbox.setEnabled(False)
                self.group_excl.setEnabled(False)
                self.TEtag.setEnabled(True)
            # repack the tags
            self.TEtag.setText(" ".join(tags))

        else:
            self.TE.setPlaceholderText(
                "Your rubric must contain some text.\n\n"
                'Prepend with "tex:" to use latex.\n\n'
                "You can harvest existing text from the page.\n\n"
                'Change "Marks" below to associate a point-change.'
            )
            self.TEtag.setPlaceholderText(
                "For any user tags you might want. (mostly future use)"
            )
            self.TEmeta.setPlaceholderText(
                "Notes about this rubric such as hints on when to use it.\n\n"
                "Not shown to student!"
            )
            self.Luser.setText(username)
        self.subsRemakeGridUI(params)
        self.hiliter.setSubs([x for x, _ in params])

    def subsMakeGridUI(self, params):
        maxver = self.maxver
        grid = QGridLayout()
        nr = 0
        if params:
            for v in range(maxver):
                grid.addWidget(QLabel(f"ver {v + 1}"), nr, v + 1)
            nr += 1

        def _func_factory(zelf, i):
            def f():
                zelf.subsRemoveRow(i)

            return f

        for i, (param, values) in enumerate(params):
            w = QLineEdit(param)
            # w.connect...  # TODO: redo syntax highlighting?
            grid.addWidget(w, nr, 0)
            for v in range(maxver):
                w = QLineEdit(values[v])
                w.setPlaceholderText(f"<value for ver{v + 1}>")
                grid.addWidget(w, nr, v + 1)
            b = QToolButton(text="➖")  # \N{Minus Sign}
            b.setToolTip("remove this parameter and values")
            b.setAutoRaise(True)
            f = _func_factory(self, i)
            b.pressed.connect(f)
            grid.addWidget(b, nr, maxver + 1)
            nr += 1

        if params:
            b = QToolButton(text="➕ add another")
        else:
            b = QToolButton(text="➕ add a parameterized substitution")
            # disabled for Issue #2462
            if not self.use_experimental_features:
                b.setEnabled(False)
        b.setAutoRaise(True)
        b.pressed.connect(self.subsAddRow)
        s = "Inserted at cursor point; highlighted text as initial value"
        if not self.use_experimental_features:
            s = "[disabled, experimental] " + s
        b.setToolTip(s)
        grid.addWidget(b, nr, 0)
        nr += 1
        return grid

    def subsAddRow(self):
        params = self.get_parameters()
        current_param_names = [p for p, _ in params]
        # find a new parameter name not yet used
        n = 1
        while True:
            new_param = "{param" + str(n) + "}"
            new_param_alt = f"<param{n}>"
            if (
                new_param not in current_param_names
                and new_param_alt not in current_param_names
            ):
                break
            n += 1
        if self.TE.toPlainText().startswith("tex:"):  # casefold?
            new_param = new_param_alt

        # we insert the new parameter at the cursor/selection
        tc = self.TE.textCursor()
        # save the selection as the new parameter value for this version
        values = ["" for _ in range(self.maxver)]
        if tc.hasSelection():
            values[self.version - 1] = tc.selectedText()
        params.append([new_param, values])
        self.hiliter.setSubs([x for x, _ in params])
        self.TE.textCursor().insertText(new_param)
        self.subsRemakeGridUI(params)

    def subsRemoveRow(self, i=0):
        params = self.get_parameters()
        params.pop(i)
        self.hiliter.setSubs([x for x, _ in params])
        self.subsRemakeGridUI(params)

    def subsRemakeGridUI(self, params):
        # discard the old grid and sub in a new one
        idx = self.scope_frame.layout().indexOf(self._param_grid)
        # print(f"discarding old grid at layout index {idx} to build new one")
        layout = self.scope_frame.layout().takeAt(idx)
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()
        layout.deleteLater()
        grid = self.subsMakeGridUI(params)
        # self.scope_frame.layout().addLayout(grid)
        self.scope_frame.layout().insertLayout(idx, grid)
        self._param_grid = grid

    def get_parameters(self):
        """Extract the current parametric values from the UI."""
        idx = self.scope_frame.layout().indexOf(self._param_grid)
        # print(f"extracting parameters from grid at layout index {idx}")
        layout = self.scope_frame.layout().itemAt(idx)
        N = layout.rowCount()
        params = []
        for r in range(1, N - 1):
            param = layout.itemAtPosition(r, 0).widget().text()
            values = []
            for c in range(1, self.maxver + 1):
                values.append(layout.itemAtPosition(r, c).widget().text())
            params.append([param, values])
        return params

    def add_new_group(self):
        groups = []
        for n in range(self.group_combobox.count()):
            groups.append(self.group_combobox.itemText(n))
        suggested_name = next_in_longest_subsequence(groups)
        s, ok = QInputDialog.getText(
            self,
            "New group for rubric",
            "<p>New group for rubric.</p><p>(Currently no spaces allowed.)</p>",
            QLineEdit.Normal,
            suggested_name,
        )
        if not ok:
            return
        s = s.strip()
        if not s:
            return
        if " " in s:
            return
        n = self.group_combobox.count()
        self.group_combobox.insertItem(n, s)
        self.group_combobox.setCurrentIndex(n)

    def changedReapableCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.reapable_CB.currentText())

    def toggle_version_specific(self):
        if self.version_specific_cb.isChecked():
            self.version_specific_le.setText(str(self.version))
            self.version_specific_le.setPlaceholderText("")
            self.version_specific_le.setEnabled(True)
        else:
            self.version_specific_le.setText("")
            self.version_specific_le.setPlaceholderText(
                ", ".join(str(x + 1) for x in range(self.maxver))
            )
            self.version_specific_le.setEnabled(False)

    def toggle_scope_elements(self):
        if self.scopeButton.isChecked():
            self.scopeButton.setArrowType(Qt.DownArrow)
            # QFormLayout.setRowVisible but only in Qt 6.4!
            # instead we are using a QFrame
            self.scope_frame.setVisible(True)
        else:
            self.scopeButton.setArrowType(Qt.RightArrow)
            self.scope_frame.setVisible(False)

    def validate_and_accept(self):
        """Make sure rubric is valid before accepting"""
        txt = self.TE.toPlainText().strip()
        if len(txt) <= 0:
            WarnMsg(
                self,
                "Your rubric must contain some text.",
                info="No whitespace only rubrics.",
                info_pre=False,
            ).exec()
            return
        if txt == ".":
            WarnMsg(
                self,
                f"Invalid text &ldquo;<tt>{txt}</tt>&rdquo; for rubric",
                info="""
                   <p>A single full-stop has meaning internally (as a sentinel),
                   so we cannot let you make one.  See
                   <a href="https://gitlab.com/plom/plom/-/issues/2421">Issue #2421</a>
                   for details.</p>
                """,
                info_pre=False,
            ).exec()
            return
        self.accept()

    def gimme_rubric_data(self):
        txt = self.TE.toPlainText().strip()  # we know this has non-zero length.
        tags = self.TEtag.text().strip()
        if self.group_checkbox.isChecked():
            group = self.group_combobox.currentText()
            # quote spacs
            if " " in group:
                group = '"' + group + '"'
                raise NotImplementedError("groups with spaces not implemented")
            if self.group_excl.isChecked():
                tag = f"group:{group} exclusive:{group}"
            else:
                tag = f"group:{group}"
            if tags:
                tags = tag + " " + tags
            else:
                tags = tag

        meta = self.TEmeta.toPlainText().strip()
        if self.typeRB_neutral.isChecked():
            kind = "neutral"
            value = 0
            out_of = 0
            display_delta = "."
        elif self.typeRB_relative.isChecked():
            kind = "relative"
            value = self.SB.value()
            out_of = 0
            display_delta = str(value) if value < 0 else f"+{value}"
        elif self.typeRB_absolute.isChecked():
            kind = "absolute"
            value = self.rubric_value_SB.value()
            out_of = self.rubric_out_of_SB.value()
            display_delta = f"{value} of {out_of}"
        else:
            raise RuntimeError("no radio was checked")
        username = self.Luser.text().strip()
        # only meaningful if we're modifying
        rubricID = self.label_rubric_id.text().strip()

        if self.version_specific_cb.isChecked():
            vers = self.version_specific_le.text()
            vers = vers.strip("[]")
            if vers:
                vers = [int(x) for x in vers.split(",")]
        else:
            vers = []

        params = self.get_parameters()

        return {
            "id": rubricID,
            "kind": kind,
            "display_delta": display_delta,
            "value": value,
            "out_of": out_of,
            "text": txt,
            "tags": tags,
            "meta": meta,
            "username": username,
            "question": self.question_number,
            "versions": vers,
            "parameters": params,
        }
