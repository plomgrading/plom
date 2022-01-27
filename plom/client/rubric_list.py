# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Forest Kobayashi

import html
import logging
from textwrap import shorten

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPalette, QCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QLabel,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from plom.misc_utils import next_in_longest_subsequence
from .useful_classes import ErrorMessage, SimpleQuestion
from .rubric_wrangler import RubricWrangler

log = logging.getLogger("annotr")

abs_suffix = " / N"
abs_suffix_length = len(abs_suffix)


def isLegalRubric(mss, kind, delta):
    """Checks the 'legality' of the current rubric - returning one of three possible states
    0 = incompatible - the kind of rubric is not compatible with the current state
    1 = compatible but out of range - the kind of rubric is compatible with the state but applying that rubric will take the score out of range [0, maxmark] (so cannot be used)
    2 = compatible and in range - is compatible and can be used.
    Note that the rubric lists use the result to decide which rubrics will be shown (return value 2) which hidden (0 return) and greyed out (1 return)


    Args:
        mss (list): triple that encodes max-mark, state, and current-score
        kind: the kind of the rubric being checked
        delta: the delta of the rubric being checked

    Returns:
        int: 0,1,2.
    """
    maxMark = mss[0]
    state = mss[1]
    score = mss[2]

    # easy cases first
    # when state is neutral - all rubrics are fine
    # a neutral rubric is always compatible and in range
    if state == "neutral" or kind == "neutral":
        return 2
    # now, neither state nor kind are neutral

    # consequently if state is absolute, no remaining rubric is legal
    # similarly, if kind is absolute, the rubric is not legal since state is not neutral
    if state == "absolute" or kind == "absolute":
        return 0

    # now state must be up or down, and kind must be delta or relative
    # delta mark = delta = must be an non-zero int.
    idelta = int(delta)
    if state == "up":
        if idelta < 0:  # not compat
            return 0
        elif idelta + score > maxMark:  # out of range
            return 1
        else:
            return 2
    else:  # state == "down"
        if idelta > 0:  # not compat
            return 0
        elif idelta + score < 0:  # out of range
            return 1
        else:
            return 2


class RubricTable(QTableWidget):
    def __init__(self, parent, shortname=None, sort=False, tabType=None):
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
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Key", "Username", "Delta", "Text", "Kind"])
        self.hideColumn(0)
        self.hideColumn(1)
        self.hideColumn(4)
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
        log.debug("tab %s changing name to %s", self.shortname, newname)
        self.shortname = newname
        # TODO: assumes parent is TabWidget, can we do with signals/slots?
        # More like "If anybody cares, I just changed my name!"
        self._parent.update_tab_names()

    def is_user_tab(self):
        return self.tabType is None

    def is_delta_tab(self):
        return self.tabType == "delta"

    def is_hidden_tab(self):
        # TODO: naming here is confusing
        return self.tabType == "hide"

    def is_shared_tab(self):
        return self.tabType == "show"

    def contextMenuEvent(self, event):
        if self.is_hidden_tab():
            self.hideContextMenuEvent(event)
        elif self.is_shared_tab():
            self.showContextMenuEvent(event)
        elif self.is_user_tab():
            self.defaultContextMenuEvent(event)
        elif self.is_delta_tab():
            self.tabContextMenuEvent(event)
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

        renameTabAction = QAction("Rename this tab...", self)
        menu.addAction(renameTabAction)
        renameTabAction.triggered.connect(self.rename_current_tab)
        a = QAction("Add new tab", self)
        a.triggered.connect(lambda: self._parent.add_new_tab())
        menu.addAction(a)
        a = QAction("Remove this tab...", self)

        def _local_delete_thyself():
            # TODO: can we put all this in some close event?
            # TODO: I don't like that we're hardcoding the parent structure here
            msg = SimpleQuestion(
                self,
                f"<p>Are you sure you want to delete the tab &ldquo;{self.shortname}&rdquo;?</p>"
                "<p>(The rubrics themselves will not be deleted).<p>",
            )
            if msg.exec_() == QMessageBox.No:
                return
            for n in range(self._parent.RTW.count()):
                tab = self._parent.RTW.widget(n)
                if tab == self:
                    self._parent.RTW.removeTab(n)
            self.clear()
            self.deleteLater()

        a.triggered.connect(_local_delete_thyself)
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

            hideAction = QAction("Hide", self)
            hideAction.triggered.connect(self.hideCurrentRubric)
            menu.addAction(hideAction)
            menu.addSeparator()
        renameTabAction = QAction("Rename this tab...", self)
        menu.addAction(renameTabAction)
        renameTabAction.triggered.connect(self.rename_current_tab)
        a = QAction("Add new tab", self)
        a.triggered.connect(lambda: self._parent.add_new_tab())
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
            event.accept()

    def rename_current_tab(self):
        # this is really a method for the current tab, not current row
        # TODO: perhaps this method is in the wrong place
        curtab_widget = self._parent.RTW.currentWidget()
        if not curtab_widget:
            return
        curname = curtab_widget.shortname
        s1, ok1 = QInputDialog.getText(
            self, 'Rename tab "{}"'.format(curname), "Enter new name"
        )
        if not ok1:
            return
        # TODO: hint that "&nice" will enable "alt-n" shortcut on most OSes
        # TODO: use a custom dialog
        # s2, ok2 = QInputDialog.getText(
        #     self, 'Rename tab "{}"'.format(curname), "Enter long name"
        # )
        log.debug('refresh tab text from "%s" to "%s"', curname, s1)
        curtab_widget.set_name(s1)

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
        self.insertRow(rc)
        self.setItem(rc, 0, QTableWidgetItem(rubric["id"]))
        self.setItem(rc, 1, QTableWidgetItem(rubric["username"]))
        if rubric["kind"] == "absolute":
            self.setItem(rc, 2, QTableWidgetItem(rubric["delta"] + abs_suffix))
        else:
            self.setItem(rc, 2, QTableWidgetItem(rubric["delta"]))
        self.setItem(rc, 3, QTableWidgetItem(rubric["text"]))
        self.setItem(rc, 4, QTableWidgetItem(rubric["kind"]))
        # set row header
        self.setVerticalHeaderItem(rc, QTableWidgetItem("{}".format(rc + 1)))
        # set the legality
        self.colourLegalRubric(rc, self._parent.mss)
        # set a tooltip over delta that tells user the type of rubric
        self.item(rc, 2).setToolTip("{}-rubric".format(rubric["kind"]))
        # set a tooltip that contains tags and meta info when someone hovers over text
        hoverText = ""
        if rubric["tags"] != "":
            hoverText += "Tagged as {}\n".format(rubric["tags"])
        if rubric["meta"] != "":
            hoverText += "{}\n".format(rubric["meta"])
        self.item(rc, 3).setToolTip(hoverText.strip())

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
            # take the manager generated delta rubrics
            if rb["username"] == "manager" and rb["kind"] == "delta":
                if (positive and int(rb["delta"]) > 0) or (
                    not positive and int(rb["delta"]) < 0
                ):
                    delta_rubrics.append(rb)

        # now sort in numerical order away from 0 and add
        for rb in sorted(delta_rubrics, key=lambda r: abs(int(r["delta"]))):
            self.appendNewRubric(rb)
        # finally append the manager-created absolute rubrics (not HAL's no-answer ones)
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
        """Move selection to the prevoous row, wrapping around if needed."""
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
        # When an item is clicked, grab the details and emit rubric signal [key, delta, text]
        r = self.getCurrentRubricRow()
        if r is None:
            r = self.firstUnhiddenRow()
            if r is None:  # there is nothing unhidden here.
                return
            self.selectRubricByRow(r)
        # recall columns are ["Key", "Username", "Delta", "Text", "Kind"])
        # absolute rubrics have trailing suffix - remove before sending signal
        delta = self.item(r, 2).text()
        if self.item(r, 4).text() == "absolute":
            delta = self.item(r, 2).text()[:-abs_suffix_length]

        self._parent.rubricSignal.emit(  # send delta, text, rubricID, kind
            [
                delta,
                self.item(r, 3).text(),
                self.item(r, 0).text(),
                self.item(r, 4).text(),
            ]
        )

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

    def colourLegalRubric(self, r, mss):
        # recall columns are ["Key", "Username", "Delta", "Text", "Kind"])
        legal = isLegalRubric(
            mss, kind=self.item(r, 4).text(), delta=self.item(r, 2).text()
        )
        colour_legal = self.palette().color(QPalette.Active, QPalette.Text)
        colour_illegal = self.palette().color(QPalette.Disabled, QPalette.Text)
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

    def updateLegalityOfDeltas(self, mss):
        """Style items according to their legality based on max,state and score (mss)"""
        for r in range(self.rowCount()):
            self.colourLegalRubric(r, mss)

    def editRow(self, tableIndex):
        r = tableIndex.row()
        rubricKey = self.item(r, 0).text()
        self._parent.edit_rubric(rubricKey)

    def updateRubric(self, new_rubric, mss):
        for r in range(self.rowCount()):
            if self.item(r, 0).text() == new_rubric["id"]:
                self.item(r, 1).setText(new_rubric["username"])
                self.item(r, 2).setText(new_rubric["delta"])
                self.item(r, 3).setText(new_rubric["text"])
                self.item(r, 4).setText(new_rubric["kind"])
                # update the legality
                self.colourLegalRubric(r, mss)
                # set a tooltip that contains tags and meta info when someone hovers over text
                hoverText = ""
                if new_rubric["tags"] != "":
                    hoverText += "Tagged as {}\n".format(new_rubric["tags"])
                if new_rubric["meta"] != "":
                    hoverText += "{}\n".format(new_rubric["meta"])
                self.item(r, 3).setToolTip(hoverText.strip())


class RubricWidget(QWidget):
    """The RubricWidget is a multi-tab interface for displaying, choosing and managing rubrics."""

    # This is picked up by the annotator and tells is what is
    # the current comment and delta
    rubricSignal = pyqtSignal(list)  # pass the rubric's [key, delta, text, kind]

    def __init__(self, parent):
        super().__init__(parent)
        self.question_number = None
        self._parent = parent
        self.username = parent.username
        self.rubrics = []
        self.maxMark = None
        self.currentScore = None
        self.currentState = None
        self.mss = [self.maxMark, self.currentState, self.currentScore]

        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        deltaP_label = "+\N{Greek Small Letter Delta}"
        deltaN_label = "\N{Minus Sign}\N{Greek Small Letter Delta}"
        self.tabS = RubricTable(self, shortname="Shared", tabType="show")
        self.tabDeltaP = RubricTable(self, shortname=deltaP_label, tabType="delta")
        self.tabDeltaN = RubricTable(self, shortname=deltaN_label, tabType="delta")
        self.RTW = QTabWidget()
        self.RTW.setMovable(True)
        self.RTW.tabBar().setChangeCurrentOnDrag(True)
        self.RTW.addTab(self.tabS, self.tabS.shortname)
        self.RTW.addTab(self.tabDeltaP, self.tabDeltaP.shortname)
        self.RTW.addTab(self.tabDeltaN, self.tabDeltaN.shortname)
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
        self.addB = QPushButton("Add")
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
        # this is all tabs: we want only the user ones
        # return [self.RTW.widget(n) for n in range(self.RTW.count())]
        L = []
        for n in range(self.RTW.count()):
            tab = self.RTW.widget(n)
            if tab.is_user_tab():
                L.append(tab)
        return L

    def update_tab_names(self):
        """Loop over the tabs and update their displayed names"""
        for n in range(self.RTW.count()):
            self.RTW.setTabText(n, self.RTW.widget(n).shortname)
            # self.RTW.setTabToolTip(n, self.RTW.widget(n).longname)

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
            tab_names = [x.shortname for x in self.user_tabs]
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
                delta = ".&nbsp;" if r["delta"] == "." else r["delta"]
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
        ).exec_()
        # TODO: could add a "Open Rubric Wrangler" button to above dialog?
        # self.wrangleRubricsInteractively()
        # TODO: if adding that, it should push tabs *again* on accept but not on cancel
        self.updateLegalityOfDeltas()

    def wrangleRubricsInteractively(self):
        wr = RubricWrangler(
            self,
            self.rubrics,
            self.get_tab_rubric_lists(),
            self.username,
            annotator_size=self._parent.size(),
        )
        if wr.exec_() != QDialog.Accepted:
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
                `tabs`, and `user_tab_names`.  The last two are lists of
                lists.  Any of these could be empty.

        If there is too much data for the number of tabs, the extra data
        is discarded.  If there is too few data, pad with empty lists
        and/or leave the current lists as they are.
        """
        if not wranglerState:
            wranglerState = {
                "user_tab_names": [],
                "shown": [],
                "hidden": [],
                "tabs": [],
            }

        # Update the wranglerState for any new rubrics not in shown/hidden (Issue #1493)
        for rubric in self.rubrics:
            # don't add HAL system rubrics
            if rubric["username"] == "HAL":
                continue
            # exclude manager-delta rubrics, see also Issue #1494
            if rubric["username"] == "manager" and rubric["kind"] == "delta":
                continue
            if (
                rubric["id"] not in wranglerState["hidden"]
                and rubric["id"] not in wranglerState["shown"]
            ):
                log.info("Appending new rubric with id {}".format(rubric["id"]))
                wranglerState["shown"].append(rubric["id"])

        # TODO: if we later deleting rubrics, this will need to deal with rubrics that
        # have disappeared from self.rubrics but still appear in some tab

        # Nicer code than below but zip truncates shorter list during length mismatch
        # for tab, name in zip(self.user_tabs, wranglerState["user_tab_names"]):
        #    tab.set_name(name)
        curtabs = self.user_tabs
        newnames = wranglerState["user_tab_names"]
        for n in range(max(len(curtabs), len(newnames))):
            if n < len(curtabs):
                if n < len(newnames):
                    curtabs[n].set_name(newnames[n])
            else:
                if n < len(newnames):
                    self.add_new_tab(newnames[n])
        del curtabs

        # compute legality for putting things in tables
        for n, tab in enumerate(self.user_tabs):
            if n >= len(wranglerState["tabs"]):
                # not enough data for number of tabs
                idlist = []
            else:
                idlist = wranglerState["tabs"][n]
            tab.setRubricsByKeys(
                self.rubrics,
                idlist,
            )
        self.tabS.setRubricsByKeys(
            self.rubrics,
            wranglerState["shown"],
        )
        self.tabDeltaP.setDeltaRubrics(self.rubrics, positive=True)
        self.tabDeltaN.setDeltaRubrics(self.rubrics, positive=False)
        self.tabHide.setRubricsByKeys(
            self.rubrics,
            wranglerState["hidden"],
        )

        # make sure something selected in each tab
        self.tabHide.selectRubricByVisibleRow(0)
        self.tabDeltaP.selectRubricByVisibleRow(0)
        self.tabDeltaN.selectRubricByVisibleRow(0)
        self.tabS.selectRubricByVisibleRow(0)
        for tab in self.user_tabs:
            tab.selectRubricByVisibleRow(0)

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

    def setQuestionNumber(self, qn):
        """Set question number being graded.

        args:
            qn (int/None): the question number.
        """
        self.question_number = qn

    def reset(self):
        """Return the widget to a no-TGV-specified state."""
        self.setQuestionNumber(None)
        log.debug("TODO - what else needs doing on reset")

    def changeMark(self, currentScore, currentState, maxMark=None):
        # Update the current and max mark and so recompute which deltas are displayed
        if maxMark:
            self.maxMark = maxMark
        self.currentScore = currentScore
        self.currentState = currentState
        self.mss = [self.maxMark, self.currentState, self.currentScore]
        self.updateLegalityOfDeltas()

    def updateLegalityOfDeltas(self):
        # now redo each tab
        self.tabS.updateLegalityOfDeltas(self.mss)
        for tab in self.user_tabs:
            tab.updateLegalityOfDeltas(self.mss)
        self.tabDeltaP.updateLegalityOfDeltas(self.mss)
        self.tabDeltaN.updateLegalityOfDeltas(self.mss)

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
        if msg.exec_() == QMessageBox.No:
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
            reapable,
            com,
            annotator_size=self._parent.size(),
        )
        if arb.exec_() != QDialog.Accepted:  # ARB does some simple validation
            return
        if arb.DE.checkState() == Qt.Checked:
            dlt = str(arb.SB.textFromValue(arb.SB.value()))
        else:
            dlt = "."
        txt = arb.TE.toPlainText().strip()  # we know this has non-zero length.
        tag = arb.TEtag.toPlainText().strip()
        meta = arb.TEmeta.toPlainText().strip()
        kind = arb.Lkind.text().strip()
        username = arb.Luser.text().strip()
        # only meaningful if we're modifying
        rubricID = arb.label_rubric_id.text().strip()

        new_rubric = {
            "kind": kind,
            "delta": dlt,
            "text": txt,
            "tags": tag,
            "meta": meta,
            "username": self.username,
            "question": self.question_number,
        }

        if edit:
            new_rubric["id"] = rubricID
            rv = self._parent.modifyRubric(rubricID, new_rubric)
            # update the rubric in the current internal rubric list
            # make sure that keys match.
            assert self.rubrics[index]["id"] == new_rubric["id"]
            # then replace
            self.rubrics[index] = new_rubric
            # update the rubric in all lists
            self.updateRubricInLists(new_rubric)
        else:
            rv = self._parent.createNewRubric(new_rubric)
            # check was updated/created successfully
            if not rv[0]:  # some sort of creation problem
                return
            # created ok
            rubricID = rv[1]
            new_rubric["id"] = rubricID
            # at this point we have an accepted new rubric
            # add it to the internal list of rubrics
            self.rubrics.append(new_rubric)
            # append the rubric to the shownList
            self.tabS.appendNewRubric(new_rubric)
            # fix for #1563 - should only add to shared list and user-generated list
            # also add it to the list in the current rubriclist (if it is a user-generated tab)
            if self.RTW.currentWidget().is_user_tab():
                self.RTW.currentWidget().appendNewRubric(new_rubric)
        # finally - select that rubric and simulate a click
        self.RTW.currentWidget().selectRubricByKey(rubricID)
        self.handleClick()

    def updateRubricInLists(self, new_rubric):
        self.tabS.updateRubric(new_rubric, self.mss)
        self.tabHide.updateRubric(new_rubric, self.mss)
        for tab in self.user_tabs:
            tab.updateRubric(new_rubric, self.mss)

    def get_tab_rubric_lists(self):
        """returns a dict of lists of the current rubrics"""
        return {
            "user_tab_names": [t.shortname for t in self.user_tabs],
            "shown": self.tabS.getKeyList(),
            "hidden": self.tabHide.getKeyList(),
            "tabs": [t.getKeyList() for t in self.user_tabs],
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


class AddRubricBox(QDialog):
    def __init__(self, parent, username, maxMark, lst, com=None, annotator_size=None):
        """Initialize a new dialog to edit/create a comment.

        Args:
            parent (QWidget): the parent window.
            username (str)
            maxMark (int)
            lst (list): these are used to "harvest" plain 'ol text
                annotations and morph them into comments.
            com (dict/None): if None, we're creating a new rubric.
                Otherwise, this has the current comment data.
            annotator_size (QSize/None): size of the parent annotator
        """
        super().__init__(parent)

        if com:
            self.setWindowTitle("Modify rubric")
        else:
            self.setWindowTitle("Add new rubric")

        # Set self to be 1/2 the size of the annotator
        if annotator_size:
            self.resize(annotator_size / 2)
        #
        self.CB = QComboBox()
        self.TE = QTextEdit()
        self.SB = SignedSB(maxMark)
        self.DE = QCheckBox("enabled")
        self.DE.setCheckState(Qt.Checked)
        self.DE.stateChanged.connect(self.toggleSB)
        self.TEtag = QTextEdit()
        self.TEmeta = QTextEdit()
        # cannot edit these
        self.label_rubric_id = QLabel("Will be auto-assigned")
        self.Luser = QLabel()
        self.Lkind = QLabel("relative")

        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        sizePolicy.setVerticalStretch(3)

        #
        self.TE.setSizePolicy(sizePolicy)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(1)
        self.TEtag.setSizePolicy(sizePolicy)
        self.TEmeta.setSizePolicy(sizePolicy)
        # TODO: make everything wider!

        flay = QFormLayout()
        flay.addRow("Enter text", self.TE)
        lay = QFormLayout()
        lay.addRow("or choose text", self.CB)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.CB.setSizePolicy(sizePolicy)
        flay.addRow("", lay)
        lay = QHBoxLayout()
        lay.addWidget(self.DE)
        lay.addItem(QSpacerItem(48, 10, QSizePolicy.Preferred, QSizePolicy.Minimum))
        lay.addWidget(self.SB)
        flay.addRow("Delta mark", lay)
        flay.addRow("Tags", self.TEtag)
        flay.addRow("Meta", self.TEmeta)

        flay.addRow("kind", self.Lkind)
        flay.addRow("Rubric ID", self.label_rubric_id)
        flay.addRow("User who created", self.Luser)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        # set up widgets
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        self.CB.addItem("")
        self.CB.addItems(lst)
        # Set up TE and CB so that when CB changed, text is updated
        self.CB.currentTextChanged.connect(self.changedCB)
        # If supplied with current text/delta then set them

        if com:
            if com["text"]:
                self.TE.clear()
                self.TE.insertPlainText(com["text"])
            if com["tags"]:
                self.TEtag.clear()
                self.TEtag.insertPlainText(com["tags"])
            if com["meta"]:
                self.TEmeta.clear()
                self.TEmeta.insertPlainText(com["meta"])
            if com["delta"]:
                if com["delta"] in [".", 0, "0"]:
                    # part of fixing #1561 - delta-spinbox was set to 0.
                    self.SB.setValue(1)
                    self.DE.setCheckState(Qt.Unchecked)
                else:
                    self.SB.setValue(int(com["delta"]))
            if com["id"]:
                self.label_rubric_id.setText(str(com["id"]))
            if com["username"]:
                self.Luser.setText(com["username"])
        else:
            self.TE.setPlaceholderText(
                "Your rubric must contain some text.\n\n"
                'Prepend with "tex:" to use latex.\n\n'
                'You can "choose text" to harvest existing text from the page.\n\n'
                'Change "delta" below to associate a point-change.'
            )
            self.TEtag.setPlaceholderText(
                "For any user tags you might want. (mostly future use)"
            )
            self.TEmeta.setPlaceholderText(
                "Notes about this rubric such as hints on when to use it.\n\n"
                "Not shown to student!"
            )
            self.Luser.setText(username)

    def changedCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.CB.currentText())

    def toggleSB(self):
        if self.DE.checkState() == Qt.Checked:
            self.SB.setEnabled(True)
            self.Lkind.setText("relative")
            # a fix for #1561 - we need to make sure delta is not zero when we enable deltas
            if self.SB.value() == 0:
                self.SB.setValue(1)
        else:
            self.Lkind.setText("neutral")
            self.SB.setEnabled(False)

    def validate_and_accept(self):
        """Make sure rubric is valid before accepting"""
        if len(self.TE.toPlainText().strip()) <= 0:  # no whitespace only rubrics
            ErrorMessage("Your rubric must contain some text.").exec_()
            return
        # make sure that when delta-enabled we dont have delta=0
        # part of fixing #1561
        if self.SB.value() == 0 and self.DE.checkState() == Qt.Checked:
            ErrorMessage(
                "If 'Delta mark' is checked then the rubric cannot have a delta of zero."
            ).exec_()
            return

        # future checks go here.
        self.accept()
