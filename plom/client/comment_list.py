# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

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
    QToolButton,
    QSpinBox,
    QTableView,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QHBoxLayout,
    QListWidgetItem,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
)

from plom.comment_utils import generate_new_comment_ID, comments_apply_default_fields


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


def commentLoadAllToml():
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
#    hide-comments-not-by-this-user
#    hide-comments-created-by-manager
default_comments_filter = [True, False, False]


def comment_relates_to_question_number(comment, question_number):
    """Return True if comment would be visible in Question #question_number.

    TODO: eventually should have a comment class: `com.isVisibileInQ(question_number)`.

    Args:
        comment (dict): A dictionary which represents the comment.
        question_number (int): A integer version of an integer indicating the
            question number.

    Returns:
        boolean: True/False.
    """

    if question_number is None:
        return False
    if int(question_number) == int(comment["question_number"]):
        return True
    else:
        return False


def comment_relates_to_username(comment, username):
    """Return True if comment would be visible because the current user created it.

    TODO: eventually should have a comment class: `com.isVisibileInU(username)`.

    Args:
        comment (dict): A dictionary which represents the comment.
        username (str): Name of the current user.
    Returns:
        boolean: True/False.
    """
    if username is None:
        return False
    if username == comment["username"] or comment["username"] == "manager":
        return True
    return False


def comment_is_default(comment):
    """Return True if comment would be visible because the it is a default comment.

    TODO: eventually should have a comment class: `com.isVisibileInDefault()`.

    Args:
        comment (dict): A dictionary which represents the comment.

    Returns:
        boolean: True/False.
    """
    if comment["username"] == "manager":
        return True
    else:
        return False


def commentIsVisible(comment, question_number, username, filters=None):
    """Check if comment visible based on question number, username, ... .

    Args:
        comment (dict): A dictionary which represents the comment.
        question_number (int): A integer version of an integer indicating the
            question number.
        username (str): Name of the current user.
        filters (list, optional): A list of True/False to indicate which
            filters are currently activated. Defaults to None.

    Returns:
        boolean: True/False for if the comment should be visible or not.
    """
    if not filters:
        filters = default_comments_filter

    filter_responses = []

    # Filter for question number.
    if filters[0] is True and not comment_relates_to_question_number(
        comment, question_number
    ):
        filter_responses.append(False)
    else:
        filter_responses.append(True)

    # Filter for username.
    if filters[1] is True and not comment_relates_to_username(comment, username):
        filter_responses.append(False)
    else:
        filter_responses.append(True)

    # Filter for default comments.
    if filters[2] is True and comment_is_default(comment):
        filter_responses.append(False)
    else:
        filter_responses.append(True)

    filter_response = all(filter_responses)

    return filter_response


class CommentWidget(QWidget):
    """A widget wrapper around the marked-comment table."""

    def __init__(self, parent, maxMark):
        # layout the widget - a table and add/delete buttons.
        super(CommentWidget, self).__init__()
        self.testname = None
        self.questnum = None
        self.tgv = None
        self.parent = parent
        self.username = parent.username
        self.maxMark = maxMark
        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        # the table has 2 cols, delta&comment.
        self.CL = SimpleCommentTable(self)
        grid.addWidget(self.CL, 1, 1, 2, 4)
        self.addB = QPushButton("Add")
        self.hideB = QPushButton("Hide")
        self.filtB = QPushButton("Filter")
        self.otherB = QToolButton()
        self.otherB.setText("\N{Anticlockwise Open Circle Arrow}")
        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.filtB, 3, 2)
        grid.addWidget(self.hideB, 3, 3)
        grid.addWidget(self.otherB, 3, 4)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.addFromTextList)
        self.hideB.clicked.connect(self.hideItem)
        self.filtB.clicked.connect(self.changeFilter)
        self.otherB.clicked.connect(self.parent.refreshComments)

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

    def hideItem(self):
        self.CL.hideItem()

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

        acb = AddCommentBox(self.username, self.maxMark, alist, self.questnum)
        if acb.exec_() == QDialog.Accepted:
            if acb.DE.checkState() == Qt.Checked:
                dlt = acb.SB.value()
            else:
                dlt = "."
            txt = acb.TE.toPlainText().strip()
            tag = acb.TEtag.toPlainText().strip()
            meta = acb.TEmeta.toPlainText().strip()
            username = acb.TEuser.text().strip()
            try:
                question_number = int(acb.TEquestnum.text().strip())
            except ValueError:
                return

            # txt has no content
            if len(txt) <= 0:
                return

            rv = self.parent.createNewRubric(
                {
                    "delta": dlt,
                    "text": txt,
                    "tags": tag,
                    "meta": meta,
                    "question": question_number,
                }
            )
            if rv[0]:  # rubric created successfully
                commentID = rv[1]
            else:  # some sort of creation problem
                return

            # TODO: we could try to carefully add this one to the table or just pull all from server: latter sounds easier for now, but more latency
            # TODO: but we should use `commentID` from above to highlight the new row at least
            self.parent.refreshComments()

    def editCurrent(self, com):
        """Open a dialog to edit a comment.

        Returns:
            dict/None: the newly updated comment or None if something
                has gone wrong or is invalid.
        """
        # text items in scene.
        lst = self.parent.getComments()
        # text items already in comment list
        clist = []
        for r in range(self.CL.cmodel.rowCount()):
            clist.append(self.CL.cmodel.index(r, 1).data())
        # text items in scene not in comment list
        alist = [X for X in lst if X not in clist]

        acb = AddCommentBox(self.username, self.maxMark, alist, self.questnum, com)
        if acb.exec_() == QDialog.Accepted:
            if acb.DE.checkState() == Qt.Checked:
                dlt = acb.SB.value()
            else:
                dlt = "."
            txt = acb.TE.toPlainText().strip()
            tag = acb.TEtag.toPlainText().strip()
            meta = acb.TEmeta.toPlainText().strip()
            username = acb.TEuser.text().strip()
            try:
                question_number = int(acb.TEquestnum.text().strip())
            except ValueError:
                return None

            # update the comment with new values
            com["delta"] = dlt
            com["text"] = txt
            com["tags"] = tag
            com["meta"] = meta
            com["count"] = 0
            com["modified"] = time.gmtime()

            # TO BE CHECKED, We just basically create a new ID
            commentID = acb.TEcommentID.text().strip()

            com["id"] = commentID
            com["username"] = username
            com["question_number"] = question_number

            # Check if the comments are similar
            add_new_comment = self.parent.checkCommentSimilarity(com)
            # input("Were they similar: "+ str(add_new_comment))
            if add_new_comment:
                com["id"] = generate_new_comment_ID()
                self.currentItem()
                # send a click to the comment button to force updates
                self.parent.ui.commentButton.animateClick()
                return com
            else:
                return None
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

        self.username = parent.username
        self.tgv = parent.tgv

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
        self.filters = default_comments_filter

        # When clicked, the selection changes, so must emit signal
        # to the annotator.
        self.pressed.connect(self.handleClick)

        # Use the row model defined above, to allow newlines inside comments
        self.cmodel = commentRowModel()
        # self.cmodel = QStandardItemModel()
        self.cmodel.setHorizontalHeaderLabels(
            ["delta", "comment", "idx", "count", "id"]
        )
        self.setModel(self.cmodel)
        # When editor finishes make sure current row re-selected.
        self.cmodel.itemChanged.connect(self.handleClick)
        # Use the delegate defined above to shade deltas when needed
        self.delegate = commentDelegate()
        self.setItemDelegate(self.delegate)

        # clear the list
        self.clist = []
        # get rubrics from server
        serverRubrics = self.parent.parent.parentMarkerUI.getRubricsFromServer()[1]
        # remove HAL generated rubrics
        # TODO: let's do this as a filter "later", similar to how we hide other user's by default
        for X in serverRubrics:
            if X["username"] == "HAL":
                continue
            self.clist.append(X)

        # TODO: deprecated, remove?
        # load_comments_toml = commentLoadAllToml()
        # toml_exists = load_comments_toml[0]

        # Creating the hidden comments list.
        self.hidden_comment_IDs = []

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

        # Hide the count and comment id as well
        self.hideColumn(3)
        self.hideColumn(4)

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

    def populateTable(self, onlyUserComments=False):
        # first erase rows but don't use .clear()

        self.cmodel.setRowCount(0)
        for i, com in enumerate(self.clist):
            # If only user comments are toggled, then only add current and
            # user's own comments.
            if onlyUserComments and (
                com["username"] != self.username and com["username"] != "manager"
            ):
                continue

            # User can edit the text, but doesn't handle drops.
            questnum = self.parent.questnum

            tgv = self.tgv

            if (
                not commentIsVisible(com, questnum, self.username, filters=self.filters)
                or com["id"] in self.hidden_comment_IDs
            ):
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

            # Setting up the counts
            counti = QStandardItem(com["count"])
            counti.setEditable(True)
            counti.setDropEnabled(False)

            # Setting up the IDs
            comIDi = QStandardItem(com["id"])
            comIDi.setEditable(True)
            comIDi.setDropEnabled(False)

            # Append it to the table.
            self.cmodel.appendRow([delti, txti, idxi, counti, comIDi])

    def handleClick(self, index=0):
        # When an item is clicked, grab the details and emit
        # the comment signal for the annotator to read.
        if index == 0:  # make sure something is selected
            self.currentItem()
        r = self.getCurrentItemRow()
        if r is not None:
            self.commentSignal.emit(
                [
                    self.cmodel.index(r, 0).data(),
                    self.cmodel.index(r, 1).data(),
                    self.cmodel.index(r, 4).data(),
                ]
            )

    def saveCommentList(self):
        comments_save_list(self.clist)

    def hideItem(self):
        """Add selected comment to the hidden list."""
        # Remove the selected row (or do nothing if no selection)
        r = self.getCurrentItemRow()
        if r is None:
            return

        # This part is for the hidden parts to be combined with the drag-dop
        #   functionality in filtering.
        # Retrieve the ID of the deleted comment in the table. Then add them
        #   to the hidden list.
        comment_to_hide_ID = self.cmodel.index(r, 4).data()
        self.hidden_comment_IDs.append(comment_to_hide_ID)

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
            self.clist.insert(idx + 1, newcom)
            # # We refresh the comments list to add the new comment to the server.
            self.parent.parent.refreshComments()
            self.populateTable()

    def focusInEvent(self, event):
        super(SimpleCommentTable, self).focusInEvent(event)
        # Now give focus back to the annotator
        self.parent.setFocus()


class AddCommentBox(QDialog):
    def __init__(self, username, maxMark, lst, questnum, com=None):
        """Initialize a new dialog to edit/create a comment.

        Args:
            username (str)
            maxMark (int)
            lst (list): these are used to "harvest" plain 'ol text
                annotations and morph them into comments.
            questnum (int)
            com (dict/None): if None, we're creating a new comment.
                Otherwise, this has the current comment data.
        """
        super().__init__()

        self.setWindowTitle("Edit comment")
        self.CB = QComboBox()
        self.TE = QTextEdit()
        self.SB = QSpinBox()
        self.DE = QCheckBox("enabled")
        self.DE.setCheckState(Qt.Checked)
        self.DE.stateChanged.connect(self.toggleSB)
        self.TEtag = QTextEdit()
        self.TEmeta = QTextEdit()
        self.TEcommentID = QLineEdit()
        self.TEuser = QLineEdit()
        # TODO: not sure what this is for but maybe it should be a combobox
        self.TEquestnum = QLineEdit()

        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        sizePolicy.setVerticalStretch(3)
        self.TE.setSizePolicy(sizePolicy)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setVerticalStretch(2)
        self.TEtag.setSizePolicy(sizePolicy)
        self.TEmeta.setSizePolicy(sizePolicy)
        # TODO: TE is still a little too tall
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
        flay.addRow("Comment ID", self.TEcommentID)
        flay.addRow("User who created", self.TEuser)
        flay.addRow("Question number", self.TEquestnum)

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
            if com["id"]:
                self.TEcommentID.setText(str(com["id"]))
            if com["username"]:
                self.TEuser.setText(com["username"])
            if com["question_number"]:
                self.TEquestnum.setText(str(com["question_number"]))
        else:
            self.TE.setPlaceholderText(
                'Prepend with "tex:" to use math.\n\n'
                'You can "Choose text" to harvest comments from an existing annotation.\n\n'
                'Change "delta" below to associate a point-change.'
            )
            self.TEmeta.setPlaceholderText(
                "notes to self, hints on when to use this comment, etc.\n\n"
                "Not shown to student!"
            )
            # TODO: is this assigned later?
            self.TEcommentID.setPlaceholderText("will be auto-assigned (???)")
            self.TEuser.setText(username)
            self.TEquestnum.setText(str(questnum))

    def changedCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.CB.currentText())

    def toggleSB(self):
        if self.DE.checkState() == Qt.Checked:
            self.SB.setEnabled(True)
        else:
            self.SB.setEnabled(False)


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
        self.cb1 = QCheckBox("Show comments from other questions")
        self.cb2 = QCheckBox("Show comments from other users (EXPERIMENTAL)")
        self.cb3 = QCheckBox("Hide preset comments from manager")
        self.cb1.setCheckState(Qt.Unchecked if curFilters[0] else Qt.Checked)
        self.cb2.setCheckState(Qt.Unchecked if curFilters[1] else Qt.Checked)
        self.cb3.setCheckState(Qt.Checked if curFilters[2] else Qt.Unchecked)
        flay = QVBoxLayout()
        flay.addWidget(self.cb1)
        flay.addWidget(self.cb2)
        flay.addWidget(self.cb3)

        # Adding the drag-drop menu for hidden comments
        self.visible_comments_list_widget = QListWidget()
        self.hidden_comments_list_widget = QListWidget()

        self.visible_comments_list_widget.setDefaultDropAction(Qt.MoveAction)
        self.hidden_comments_list_widget.setDefaultDropAction(Qt.MoveAction)

        self.hidden_comments_list_widget.setViewMode(QListWidget.ListMode)
        self.visible_comments_list_widget.setViewMode(QListWidget.ListMode)

        self.visible_comments_list_widget.setAcceptDrops(True)
        self.visible_comments_list_widget.setDragEnabled(True)
        self.hidden_comments_list_widget.setAcceptDrops(True)
        self.hidden_comments_list_widget.setDragEnabled(True)

        for comment in parent.clist:
            # careful used later where id is extracted
            w = QListWidgetItem(
                "{} Q{} [{}] {}".format(
                    comment["id"],
                    comment["question_number"],
                    comment["delta"],
                    comment["text"],
                )
            )
            if comment["id"] not in parent.hidden_comment_IDs:
                self.visible_comments_list_widget.addItem(w)
            else:
                self.hidden_comments_list_widget.addItem(w)

        self.dragdrop_layout = QFormLayout()
        self.dragdrop_layout.addRow(QLabel("Visible"), QLabel("Hidden"))
        self.dragdrop_layout.addRow(
            self.visible_comments_list_widget, self.hidden_comments_list_widget
        )
        # Done with setting up the drag-drop widgets

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vlay = QVBoxLayout()
        vlay.addLayout(flay)

        # Adding the drag-drop layout
        vlay.addLayout(self.dragdrop_layout)

        vlay.addWidget(buttons)
        self.setLayout(vlay)
        buttons.accepted.connect(self.accept)  # Overwritten to hidden comments.
        buttons.rejected.connect(self.reject)  # Not overwritten

    def accept(self):
        """Overwrite "accept" for Dialog to also update hidden comments list."""
        self.updateListUponClosing()
        self.parent.populateTable()
        super().accept()

    def updateListUponClosing(self):
        """Update the hidden comments list upon closing the widget."""
        self.parent.hidden_comment_IDs = [
            str(
                str(self.hidden_comments_list_widget.item(index).text())
                .split()[0]
                .strip()
            )
            for index in range(self.hidden_comments_list_widget.count())
        ]

    def getFilters(self):
        return [
            self.cb1.checkState() == Qt.Unchecked,
            self.cb2.checkState() == Qt.Unchecked,
            self.cb3.checkState() == Qt.Checked,
        ]
