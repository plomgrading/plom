# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

import re
import time
import logging
from pathlib import Path

import toml
import appdirs

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QDropEvent, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QLabel,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QItemDelegate,
    QPushButton,
    QSpinBox,
    QTableView,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


log = logging.getLogger("annotr")
comment_dir = Path(appdirs.user_data_dir("plom", "PlomGrading.org"))
comment_filename = "plomComments.toml"
comment_file = comment_dir / comment_filename


def comments_new_default_list():
    """Make a default list of comments."""

    # string-escaping here must match toml.dumps
    cdict = toml.loads(
        r"""
[[comment]]
delta = -1
text = "algebra"

[[comment]]
delta = -1
text = "arithmetic"

[[comment]]
delta = "."
text = "meh"

[[comment]]
delta = 0
text = "tex: you can write \\LaTeX, $e^{i\\pi}+1=0$"

[[comment]]
delta = 0
text = "be careful"

[[comment]]
delta = 1
text = "good"
meta = "give constructive feedback"

[[comment]]
delta = 1
text = "Quest. 1 specific comment"
tags = "Q1"

[[comment]]
delta = -1
text = "Quest. 2 specific comment"
tags = "Q2 foo bar"
"""
    )
    # should be a dict = {"comment": [list of stuff]}
    assert "comment" in cdict
    clist = cdict["comment"]
    return comments_apply_default_fields(clist)


def comments_apply_default_fields(comlist):
    """Add missing fields with defaults to list of comments.

    Args:
        comlist (list): list of dicts.  Copies will not be made so
            keep a deep copy if you need the original.

    Returns:
        list: updated list of dicts.
    """
    comment_defaults = {
        "tags": "",
        "testname": "",
        "meta": "",
        "created": time.gmtime(0),
        "modified": time.gmtime(0),
    }
    for d in comlist:
        for k, v in comment_defaults.items():
            d.setdefault(k, comment_defaults[k])
    return comlist


def comments_load_from_file(f):
    """Grab comments from a toml file.

    Args:
        f (str/pathlib.Path): filename of a toml file.

    Returns:
        list: list of dicts, one for each comments.

    Raises:
        FileNotFoundError:
        PermissionError:
    """
    cdict = toml.load(f)
    clist = cdict["comment"]
    return comments_apply_default_fields(clist)


def commentLoadAll():
    """Grab comments from the toml file or return defaults."""
    local_comfile = Path(comment_filename)
    comfile = comment_dir / comment_filename
    try:
        clist = comments_load_from_file(local_comfile)
        # Note: on save, central file overwritten, Issue #1355
        log.info("Loaded a LOCAL comment file: %s", local_comfile)
        return clist
    except (FileNotFoundError, PermissionError):
        pass
    try:
        clist = comments_load_from_file(comfile)
        log.info("Loaded comment file: %s", comfile)
        return clist
    except FileNotFoundError:
        pass
    clist = comments_new_default_list()
    log.info("Starting from scratch (no comment file %s)", comfile)
    return clist


def comments_save_list(clist, comment_dir=comment_dir, filename=comment_filename):
    """Export comment list to toml file."""
    # TODO: don't save empty tags/testnames/etc to file?
    comfile = comment_dir / filename
    comment_dir.mkdir(exist_ok=True)
    with open(comfile, "w") as fname:
        # toml wants a dictionary
        toml.dump({"comment": clist}, fname)
    log.info("Saved comment file: %s", comfile)


# Eventually there may be more "state" to the filters and something like a dict
# might make more sense here, but for now its list of booleans:
#    hide-comments-not-for-this-question
#    hide-comments-not-for-this-test
comDefaultFilters = [True, True]


def commentVisibleInQuestion(com, n):
    """Return True if comment would be visible in Question n.

    Either there are no Q# tags or there is a Qn tag.

    TODO: eventually should have a comment class: `com.isVisibileInQ(n)`
    """
    if n is None:
        return True
    Qn = "Q{}".format(n)
    tags = com["tags"].split()
    return any([t == Qn for t in tags]) or not any(
        [re.match(r"^Q\d+$", t) for t in tags]
    )


def commentIsVisible(com, questnum, testname, filters=None):
    """Is comment visible for this question, testname and filters?"""
    if not filters:
        filters = comDefaultFilters
    viz = True
    if filters[0] and not commentVisibleInQuestion(com, questnum):
        viz = False
    if filters[1] and com["testname"] and not com["testname"] == testname:
        viz = False
    return viz


def commentTaggedQn(com, n):
    """Return True if comment tagged for Question n.

    There is a Qn tag.
    """
    Qn = "Q{}".format(n)
    tags = com["tags"].split()
    return any([t == Qn for t in tags])


def commentHasMultipleQTags(com):
    tags = com["tags"].split()
    x = [1 if re.match(r"^Q\d+$", t) else 0 for t in tags]
    return sum(x) >= 2


class CommentWidget(QWidget):
    """A widget wrapper around the marked-comment table."""

    def __init__(self, parent, maxMark):
        # layout the widget - a table and add/delete buttons.
        super(CommentWidget, self).__init__()
        self.testname = None
        self.questnum = None
        self.parent = parent
        self.maxMark = maxMark
        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        # the table has 2 cols, delta&comment.
        self.CL = SimpleCommentTable(self)
        grid.addWidget(self.CL, 1, 1, 2, 3)
        self.addB = QPushButton("Add")
        self.delB = QPushButton("Delete")
        self.filtB = QPushButton("Filter")
        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.filtB, 3, 2)
        grid.addWidget(self.delB, 3, 3)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.addFromTextList)
        self.delB.clicked.connect(self.deleteItem)
        self.filtB.clicked.connect(self.changeFilter)

    def setTestname(self, s):
        """Set testname and refresh view."""
        self.testname = s
        self.CL.populateTable()

    def setQuestionNumber(self, n):
        """Set question number and refresh view.

        Question number can be an integer or `None`."""
        self.questnum = n
        self.CL.populateTable()

    def setStyle(self, markStyle):
        # The list needs a style-delegate because the display
        # of the delta-mark will change depending on
        # the current total mark and whether mark
        # total or up or down. Delta-marks that cannot
        # be assigned will be shaded out to indicate that
        # they will not be pasted into the window.
        self.CL.delegate.style = markStyle

    def changeMark(self, currentMark):
        # Update the current and max mark for the lists's
        # delegate so that it knows how to display the comments
        # and deltas when the mark changes.
        self.CL.delegate.maxMark = self.maxMark
        self.CL.delegate.currentMark = currentMark
        self.CL.viewport().update()

    def reset(self):
        """Return the widget to a no-TGV-specified state."""
        self.setQuestionNumber(None)
        self.setTestname(None)
        # TODO: do we need to do something about maxMark, currentMax, markStyle?
        self.CL.populateTable()

    def saveComments(self):
        self.CL.saveCommentList()

    def deleteItem(self):
        self.CL.deleteItem()

    def changeFilter(self):
        self.CL.changeFilter()

    def currentItem(self):
        # grab focus and trigger a "row selected" signal
        # in the comment list
        self.CL.currentItem()
        self.setFocus()

    def nextItem(self):
        # grab focus and trigger a "row selected" signal
        # in the comment list
        self.CL.nextItem()
        self.setFocus()

    def previousItem(self):
        # grab focus and trigger a "row selected" signal
        # in the comment list
        self.CL.previousItem()
        self.setFocus()

    def getCurrentItemRow(self):
        return self.CL.getCurrentItemRow()

    def setCurrentItemRow(self, r):
        """Reset the comment row on a new task to last highlighted comment."""
        return self.CL.setCurrentItemRow(r)

    def addFromTextList(self):
        # text items in scene.
        lst = self.parent.getComments()
        # text items already in comment list
        clist = []
        for r in range(self.CL.cmodel.rowCount()):
            clist.append(self.CL.cmodel.index(r, 1).data())
        # text items in scene not in comment list
        alist = [X for X in lst if X not in clist]

        acb = AddCommentBox(self, self.maxMark, alist, self.questnum, self.testname)
        if acb.exec_() == QDialog.Accepted:
            if acb.DE.checkState() == Qt.Checked:
                dlt = acb.SB.value()
            else:
                dlt = "."
            txt = acb.TE.toPlainText().strip()
            tag = acb.TEtag.toPlainText().strip()
            meta = acb.TEmeta.toPlainText().strip()
            testnames = acb.TEtestname.text().strip()
            # check if txt has any content
            if len(txt) > 0:
                com = {
                    "delta": dlt,
                    "text": txt,
                    "tags": tag,
                    "testname": testnames,
                    "meta": meta,
                    "created": time.gmtime(),
                    "modified": time.gmtime(),
                }
                self.CL.insertItem(com)
                self.currentItem()
                # send a click to the comment button to force updates
                self.parent.ui.commentButton.animateClick()

    def editCurrent(self, com):
        # text items in scene.
        lst = self.parent.getComments()
        # text items already in comment list
        clist = []
        for r in range(self.CL.cmodel.rowCount()):
            clist.append(self.CL.cmodel.index(r, 1).data())
        # text items in scene not in comment list
        alist = [X for X in lst if X not in clist]
        questnum = self.questnum
        testname = self.testname
        acb = AddCommentBox(self, self.maxMark, alist, questnum, testname, com)
        if acb.exec_() == QDialog.Accepted:
            if acb.DE.checkState() == Qt.Checked:
                dlt = acb.SB.value()
            else:
                dlt = "."
            txt = acb.TE.toPlainText().strip()
            tag = acb.TEtag.toPlainText().strip()
            meta = acb.TEmeta.toPlainText().strip()
            testnames = acb.TEtestname.text().strip()
            # update the comment with new values
            com["delta"] = dlt
            com["text"] = txt
            com["tags"] = tag
            com["testname"] = testnames
            com["meta"] = meta
            com["modified"] = time.gmtime()
            return com
        else:
            return None


class commentDelegate(QItemDelegate):
    """A style delegate that changes how rows of the
    comment list are displayed. In particular, the
    delta will be shaded out if it cannot be applied
    given the current mark and the max mark.
    Eg - if marking down then all positive delta are shaded
    if marking up then all negative delta are shaded
    if mark = 7/10 then any delta >= 4 is shaded.
    """

    def __init__(self):
        super(commentDelegate, self).__init__()
        self.currentMark = 0
        self.maxMark = 0
        self.style = 0

    def paint(self, painter, option, index):
        # Only run the standard delegate if flag is true.
        # else don't paint anything.
        flag = True
        # Only shade the deltas which are in col 0.
        if index.column() == 0:
            # Grab the delta value.
            delta = index.model().data(index, Qt.EditRole)
            if delta == ".":
                flag = True
            elif self.style == 2:
                # mark up - shade negative, or if goes past max mark
                if int(delta) < 0 or int(delta) + self.currentMark > self.maxMark:
                    flag = False
            elif self.style == 3:
                # mark down - shade positive, or if goes below 0
                if int(delta) > 0 or int(delta) + self.currentMark < 0:
                    flag = False
            elif self.style == 1:
                # mark-total - do not show deltas.
                flag = False
        if flag:
            QItemDelegate.paint(self, painter, option, index)


class commentRowModel(QStandardItemModel):
    """Need to alter the standrd item model so that when we
    drag/drop to rearrange things, the whole row is moved,
    not just the item. Solution found at (and then tweaked)
    https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget/43789304#43789304
    """

    def setData(self, index, value, role=Qt.EditRole):
        """Simple validation of data in the row. Also convert
        an escaped '\n' into an actual newline for multiline
        comments.
        """
        # check that data in column zero is numeric
        if index.column() == 0:  # try to convert value to integer
            try:
                v = int(value)  # success! is number
                if v > 0:  # if it is positive, then make sure string is "+v"
                    value = "+{}".format(v)
                # otherwise the current value is "0" or "-n".
            except ValueError:
                value = "."  # failed, so set to "."
        # If its column 1 then convert '\n' into actual newline in the string
        elif index.column() == 1:
            value = value.replace(
                "\\n ", "\n"
            )  # so we can latex commands that start with \n
        return super().setData(index, value, role)


class SimpleCommentTable(QTableView):
    """The comment table needs to signal the annotator to tell
    it what the current comment and delta are.
    Also needs to know the current/max mark and marking style
    in order to change the shading of the delta that goes with
    each comment.

    Dragdrop rows solution found at (and tweaked)
    https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget/43789304#43789304
    """

    # This is picked up by the annotator and tells is what is
    # the current comment and delta
    commentSignal = pyqtSignal(list)

    def __init__(self, parent):
        super(SimpleCommentTable, self).__init__()
        self.parent = parent
        # No numbers down the left-side
        self.verticalHeader().hide()
        # The comment column should be as wide as possible
        self.horizontalHeader().setStretchLastSection(True)
        # Only select one row at a time.
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Drag and drop rows to reorder and also paste into pageview
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.filters = comDefaultFilters

        # When clicked, the selection changes, so must emit signal
        # to the annotator.
        self.pressed.connect(self.handleClick)

        # Use the row model defined above, to allow newlines inside comments
        self.cmodel = commentRowModel()
        # self.cmodel = QStandardItemModel()
        self.cmodel.setHorizontalHeaderLabels(["delta", "comment", "idx"])
        self.setModel(self.cmodel)
        # When editor finishes make sure current row re-selected.
        self.cmodel.itemChanged.connect(self.handleClick)
        # Use the delegate defined above to shade deltas when needed
        self.delegate = commentDelegate()
        self.setItemDelegate(self.delegate)
        # A list of comments
        self.clist = commentLoadAll()
        self.populateTable()
        # put these in a timer(0) so they exec when other stuff done
        QTimer.singleShot(0, self.resizeRowsToContents)
        QTimer.singleShot(0, self.resizeColumnsToContents)
        # If an item is changed resize things appropriately.
        self.cmodel.itemChanged.connect(self.resizeRowsToContents)

        # set this so no (native) edit. Instead we'll hijack double-click
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.doubleClicked.connect(self.editRow)
        self.hideColumn(2)

    def dropEvent(self, event: QDropEvent):
        # If drag and drop from self to self.
        if not event.isAccepted() and event.source() == self:
            # grab the row number of dragged row and its data
            row = self.selectedIndexes()[0].row()
            idx = self.cmodel.index(row, 2).data()
            # Get the row on which to drop
            dropRow = self.drop_on(event)
            dropIdx = self.cmodel.index(dropRow, 2).data()
            log.debug(
                "debug DnD: drag={}, drop={}".format((row, idx), (dropRow, dropIdx))
            )
            # If we drag from earlier row, handle index after deletion
            if row < dropRow:
                dropRow -= 1
            # TODO: maybe `row` does not account for hidden rows, changed to `idx`
            com = self.clist.pop(int(idx))
            log.debug("debug DnD: com of row drag is {}".format(com))
            self.clist.insert(dropRow, com)
            self.populateTable()

            # Reselect the dropped row (TODO: does this work?)
            # TODO: sometimes dropRow is None (drag to end?)
            self.selectRow(dropRow)

            # Resize the rows - they were expanding after drags for some reason
            # TODO: remove?
            self.resizeRowsToContents()
        else:
            super().dropEvent(event)

    def drop_on(self, event):
        # Where is the drop event - which row
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.cmodel.rowCount()
        if self.isBelow(event.pos(), index):
            return index.row() + 1
        else:
            return index.row()

    def isBelow(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() < rect.top() + margin:
            return False
        elif rect.bottom() < pos.y() + margin:
            return True
        # noinspection PyTypeChecker
        return (
            rect.contains(pos, True)
            and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled)
            and pos.y() >= rect.center().y()
        )

    def populateTable(self):
        # first erase rows but don't use .clear()
        self.cmodel.setRowCount(0)
        for i, com in enumerate(self.clist):
            # User can edit the text, but doesn't handle drops.
            questnum = self.parent.questnum
            testname = self.parent.testname
            if not commentIsVisible(com, questnum, testname, filters=self.filters):
                continue
            txti = QStandardItem(com["text"])
            txti.setEditable(True)
            txti.setDropEnabled(False)
            dlt = com["delta"]
            # If delta>0 then should be "+n"
            if dlt == ".":
                delti = QStandardItem(".")
            elif int(dlt) > 0:
                delti = QStandardItem("+{}".format(int(dlt)))
            else:
                # is zero or negative - is "0" or "-n"
                delti = QStandardItem("{}".format(dlt))
            # User can edit the delta, but doesn't handle drops.
            delti.setEditable(True)
            delti.setDropEnabled(False)
            delti.setTextAlignment(Qt.AlignCenter)
            idxi = QStandardItem(str(i))
            idxi.setEditable(False)
            idxi.setDropEnabled(False)
            # Append it to the table.
            self.cmodel.appendRow([delti, txti, idxi])

    def handleClick(self, index=0):
        # When an item is clicked, grab the details and emit
        # the comment signal for the annotator to read.
        if index == 0:  # make sure something is selected
            self.currentItem()
        r = self.getCurrentItemRow()
        if r is not None:
            self.commentSignal.emit(
                [self.cmodel.index(r, 0).data(), self.cmodel.index(r, 1).data()]
            )

    def saveCommentList(self):
        comments_save_list(self.clist)

    def deleteItem(self):
        # Remove the selected row (or do nothing if no selection)
        r = self.getCurrentItemRow()
        if r is None:
            return
        idx = int(self.cmodel.index(r, 2).data())
        self.clist.pop(idx)
        # TODO: maybe sloppy to rebuild, need automatic cmodel ontop of clist
        self.populateTable()

    def changeFilter(self):
        d = ChangeFiltersDialog(self, self.filters)
        if d.exec_() == QDialog.Accepted:
            newfilters = d.getFilters()
            self.filters = newfilters
            # TODO: maybe sloppy to rebuild, need automatic cmodel ontop of clist
            self.populateTable()

    def currentItem(self):
        # If no selected row, then select row 0.
        # else select current row - triggers a signal.
        r = self.getCurrentItemRow()
        if r is None:
            if self.cmodel.rowCount() >= 1:
                r = 0
        self.setCurrentItemRow(r)

    def getCurrentItemRow(self):
        """Return the currently-selected row or None if no selection."""
        if not self.selectedIndexes():
            return None
        return self.selectedIndexes()[0].row()

    def setCurrentItemRow(self, r):
        """Reset the comment row on a new task to last highlighted comment.

        Args:
            r (int): The integer representing the row number in the
                comments table.  If r is None, do nothing.
        """
        if r is not None:
            self.selectRow(r)

    def nextItem(self):
        """Move selection to the next row, wrapping around if needed."""
        r = self.getCurrentItemRow()
        if r is None:
            if self.cmodel.rowCount() >= 1:
                r = 0
            else:
                return
        r = (r + 1) % self.cmodel.rowCount()
        self.setCurrentItemRow(r)

    def previousItem(self):
        """Move selection to the prevoous row, wrapping around if needed."""
        r = self.getCurrentItemRow()
        if r is None:
            if self.cmodel.rowCount() >= 1:
                r = 0
            else:
                return
        r = (r - 1) % self.cmodel.rowCount()
        self.setCurrentItemRow(r)

    def insertItem(self, com):
        self.clist.append(com)
        self.populateTable()

    def editRow(self, tableIndex):
        r = tableIndex.row()
        idx = int(self.cmodel.index(r, 2).data())
        com = self.clist[idx]
        newcom = self.parent.editCurrent(com)
        if newcom is not None:
            self.clist[idx] = newcom
            self.populateTable()

    def focusInEvent(self, event):
        super(SimpleCommentTable, self).focusInEvent(event)
        # Now give focus back to the annotator
        self.parent.setFocus()


class AddCommentBox(QDialog):
    def __init__(self, parent, maxMark, lst, questnum, curtestname, com=None):
        super(QDialog, self).__init__()
        self.parent = parent
        self.questnum = questnum
        self.setWindowTitle("Edit comment")
        self.CB = QComboBox()
        self.TE = QTextEdit()
        self.SB = QSpinBox()
        self.DE = QCheckBox("Delta-mark enabled")
        self.DE.setCheckState(Qt.Checked)
        self.DE.stateChanged.connect(self.toggleSB)
        self.TEtag = QTextEdit()
        self.TEmeta = QTextEdit()
        self.TEtestname = QLineEdit()
        # TODO: how to make it smaller vertically than the TE?
        # self.TEtag.setMinimumHeight(self.TE.minimumHeight() // 2)
        # self.TEtag.setMaximumHeight(self.TE.maximumHeight() // 2)
        self.QSpecific = QCheckBox("Available only in question {}".format(questnum))
        self.QSpecific.stateChanged.connect(self.toggleQSpecific)

        flay = QFormLayout()
        flay.addRow("Enter text", self.TE)
        flay.addRow("Choose text", self.CB)
        flay.addRow("Set delta", self.SB)
        flay.addRow("", self.DE)
        flay.addRow("", self.QSpecific)
        flay.addRow("Tags", self.TEtag)
        # TODO: support multiple tests, change label to "test(s)" here
        flay.addRow("Specific to test", self.TEtestname)
        flay.addRow("", QLabel("(leave blank to share between tests)"))
        flay.addRow("Meta", self.TEmeta)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        # set up widgets
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.SB.setRange(-maxMark, maxMark)
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
                if com["delta"] == ".":
                    self.SB.setValue(0)
                    self.DE.setCheckState(Qt.Unchecked)
                else:
                    self.SB.setValue(int(com["delta"]))
            if com["testname"]:
                self.TEtestname.setText(com["testname"])
            # TODO: ideally we would do this on TE change signal
            # TODO: textEdited() signal (not textChanged())
            if commentHasMultipleQTags(com):
                self.QSpecific.setEnabled(False)
            elif commentTaggedQn(com, self.questnum):
                self.QSpecific.setCheckState(Qt.Checked)
            else:
                self.QSpecific.setCheckState(Qt.Unchecked)
        else:
            self.TEtestname.setText(curtestname)
            self.QSpecific.setCheckState(Qt.Checked)
            self.TE.setPlaceholderText(
                'Prepend with "tex:" to use math.\n\n'
                'You can "Choose text" to harvest comments from an existing annotation.\n\n'
                'Change "delta" below to set a point-change associated with this comment.'
            )
            self.TEmeta.setPlaceholderText(
                "notes to self, hints on when to use this comment, etc.\n\n"
                "Not shown to student!"
            )

    def changedCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.CB.currentText())

    def toggleSB(self):
        if self.DE.checkState() == Qt.Checked:
            self.SB.setEnabled(True)
        else:
            self.SB.setEnabled(False)

    def toggleQSpecific(self):
        tags = self.TEtag.toPlainText().split()
        Qn = "Q{}".format(self.questnum)
        if self.QSpecific.checkState() == Qt.Checked:
            if not Qn in tags:
                tags.insert(0, Qn)
                self.TEtag.clear()
                self.TEtag.insertPlainText(" ".join(tags))
        else:
            if Qn in tags:
                tags.remove(Qn)
                self.TEtag.clear()
                self.TEtag.insertPlainText(" ".join(tags))


class AddTagBox(QDialog):
    def __init__(self, parent, currentTag, tagList=[]):
        super(QDialog, self).__init__()
        self.parent = parent
        self.CB = QComboBox()
        self.TE = QTextEdit()

        flay = QFormLayout()
        flay.addRow("Enter tag\n(max 256 char)", self.TE)
        flay.addRow("Choose tag", self.CB)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        # set up widgets
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.CB.addItem("")
        self.CB.addItems(tagList)
        # Set up TE and CB so that when CB changed, text is updated
        self.CB.currentTextChanged.connect(self.changedCB)
        # If supplied with current text/delta then set them
        if currentTag is not None:
            self.TE.clear()
            self.TE.insertPlainText(currentTag)

    def changedCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.CB.currentText())


class ChangeFiltersDialog(QDialog):
    def __init__(self, parent, curFilters):
        super(QDialog, self).__init__()
        self.parent = parent
        self.cb1 = QCheckBox("Hide comments from other questions")
        self.cb2 = QCheckBox("Hide comments from other tests")
        self.cb1.setCheckState(Qt.Checked if curFilters[0] else Qt.Unchecked)
        if curFilters[1]:
            self.cb2.setCheckState(Qt.Checked)
        else:
            self.cb2.setCheckState(Qt.Unchecked)

        flay = QVBoxLayout()
        flay.addWidget(self.cb1)
        flay.addWidget(self.cb2)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def getFilters(self):
        return [
            self.cb1.checkState() == Qt.Checked,
            self.cb2.checkState() == Qt.Checked,
        ]
