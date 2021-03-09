# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

import logging
from pathlib import Path

import toml
import appdirs

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QDropEvent,
    QStandardItem,
    QStandardItemModel,
)
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
    QItemDelegate,
    QMessageBox,
    QMenu,
    QPushButton,
    QToolButton,
    QSpinBox,
    QTabBar,
    QTabWidget,
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

from plom.comment_utils import comments_apply_default_fields
from .useful_classes import ErrorMessage, SimpleMessage
from .rubric_wrangler import RubricWrangler

log = logging.getLogger("annotr")
comment_dir = Path(appdirs.user_data_dir("plom", "PlomGrading.org"))
comment_filename = "plomComments.toml"
comment_file = comment_dir / comment_filename


def deltaToInt(x):
    """Since delta can just be a . """
    if x == ".":
        return 0
    else:
        return int(x)


# colours to indicate whether rubric is legal to paste or not.
colour_legal = QBrush(QColor(0, 0, 0))
colour_illegal = QBrush(QColor(128, 128, 128, 128))


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
#    hide-comments-not-for-this-question (recommended)
#    hide-comments-not-by-this-user
#    hide-comments-created-by-manager
#    hide-comments-created-by-system (recommended)
default_comments_filter = [True, False, False, True]


def comment_is_question_number(comment, question_number):
    """Return True if comment created for question_number.

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
    return int(question_number) == int(comment["question_number"])


def comment_is_username_or_manager(comment, username):
    """Return True if comment created by user=username or manager

    TODO: eventually should have a comment class: `com.isVisibileInU(username)`.

    Args:
        comment (dict): A dictionary which represents the comment.
        username (str): Name of the current user.
    Returns:
        boolean: True/False.
    """
    if username is None:
        return False
    return comment["username"] in [username, "manager"]


def comment_is_manager(comment):
    """Return True if comment manager-generated

    TODO: eventually should have a comment class: `com.isVisibileInDefault()`.

    Args:
        comment (dict): A dictionary which represents the comment.

    Returns:
        boolean: True/False.
    """
    return comment["username"] == "manager"


def comment_is_system(comment):
    """Return True if comment is system-generated

    TODO: eventually should have a comment class: `com.isVisibileInDefault()`.

    Args:
        comment (dict): A dictionary which represents the comment.

    Returns:
        boolean: True/False.
    """
    return comment["username"] == "HAL"


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

    # 0=  hide-comments-not-for-this-question
    # 1=  hide-comments-not-by-this-user(or manager)
    # 2=  hide-comments-created-by-manager
    # 3=  hide-comments-created-by-system

    # Filter for question number.
    if filters[0] is True and not comment_is_question_number(comment, question_number):
        return False
    # Filter for username.
    if filters[1] is True and not comment_is_username_or_manager(comment, username):
        return False
    # Filter for Manager comments.
    if filters[2] is True and comment_is_manager(comment):
        return False
    # Filter for System comments.
    if filters[3] is True and comment_is_system(comment):
        return False
    # passed all filters
    return True


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
        self._fake_tabz = QLabel("Tabs | <b>Rubric Panes</b> | Go | Here | TODO")
        grid.addWidget(self._fake_tabz, 0, 0, 1, 4, Qt.AlignHCenter | Qt.AlignTop)
        self.CL = SimpleCommentTable(self)
        grid.addWidget(self.CL, 1, 0, 1, 4)
        self.addB = QPushButton("Add")
        self.hideB = QPushButton("Hide")
        self.filtB = QPushButton("Filter")
        self.otherB = QToolButton()
        self.otherB.setText("\N{Anticlockwise Open Circle Arrow}")
        grid.addWidget(self.addB, 2, 0)
        grid.addWidget(self.filtB, 2, 1)
        grid.addWidget(self.hideB, 2, 2)
        grid.addWidget(self.otherB, 2, 3)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.add_new_comment)
        self.hideB.clicked.connect(self.hideItem)
        self.filtB.clicked.connect(self.changeFilter)
        self.otherB.clicked.connect(self.parent.refreshRubrics)
        # get rubrics
        self.parent.refreshRubrics()

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

    def get_nonrubric_text_from_page(self):
        """Find any text that isn't already part of a formal rubric.

        Returns:
            list: TODO: type of these?
        """
        text_items = self.parent.getComments()
        # text items already in comment list
        clist = []
        for r in range(self.CL.cmodel.rowCount()):
            clist.append(self.CL.cmodel.index(r, 1).data())
        return [x for x in text_items if x not in clist]

    def add_new_comment(self):
        """Open a dialog to create a new comment."""
        self._new_or_edit_comment(None)

    def edit_comment(self, com):
        """Open a dialog to edit a comment."""
        if com["username"] == self.username:
            self._new_or_edit_comment(com, edit=True)
            return
        msg = SimpleMessage(
            "<p>You did not create this message.</p>"
            "<p>To edit it, the system will make a copy that you can edit.</p>"
            "<p>Do you want to continue?</p>"
        )
        if msg.exec_() == QMessageBox.No:
            return
        com = com.copy()  # don't muck-up the original
        com["id"] = None
        com["username"] = self.username
        self._new_or_edit_comment(com, edit=False)

    def _new_or_edit_comment(self, com, edit=False):
        """Open a dialog to edit a comment or make a new one.

        args:
            com (dict/None): a comment to modify or use as a template
                depending on next arg.  If set to None, which always
                means create new.
            edit (bool): are we modifying the comment?  if False, use
                `com` as a template for a new duplicated comment.

        Returns:
            None: does its work through side effects on the comment list.
        """
        reapable = self.get_nonrubric_text_from_page()
        acb = AddCommentBox(self.username, self.maxMark, reapable, self.questnum, com)
        if acb.exec_() != QDialog.Accepted:
            return
        if acb.DE.checkState() == Qt.Checked:
            dlt = acb.SB.value()
        else:
            dlt = "."
        txt = acb.TE.toPlainText().strip()
        if len(txt) <= 0:
            return
        tag = acb.TEtag.toPlainText().strip()
        meta = acb.TEmeta.toPlainText().strip()
        username = acb.TEuser.text().strip()
        # only meaningful if we're modifying
        commentID = acb.label_rubric_id.text().strip()
        try:
            question_number = int(acb.TEquestnum.text().strip())
        except ValueError:
            return

        if edit:
            rv = self.parent.modifyRubric(
                commentID,
                {
                    "id": commentID,
                    "delta": dlt,
                    "text": txt,
                    "tags": tag,
                    "meta": meta,
                    "question": question_number,
                },
            )
        else:
            rv = self.parent.createNewRubric(
                {
                    "delta": dlt,
                    "text": txt,
                    "tags": tag,
                    "meta": meta,
                    "question": question_number,
                },
            )
        if rv[0]:  # rubric created successfully
            commentID = rv[1]
        else:  # some sort of creation problem
            return

        # TODO: we could try to carefully add this one to the table or just pull all from server: latter sounds easier for now, but more latency
        # TODO: but we should use `commentID` from above to highlight the new row at least
        self.parent.refreshRubrics()
        # send a click to the comment button to force updates
        self.parent.ui.commentButton.animateClick()


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
        self.setAcceptDrops(False)
        self.viewport().setAcceptDrops(False)
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
        return
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
        self.parent.edit_comment(com)

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

        if com:
            self.setWindowTitle("Modify comment")
        else:
            self.setWindowTitle("Add new comment")
        self.CB = QComboBox()
        self.TE = QTextEdit()
        self.SB = QSpinBox()
        self.DE = QCheckBox("enabled")
        self.DE.setCheckState(Qt.Checked)
        self.DE.stateChanged.connect(self.toggleSB)
        self.TEtag = QTextEdit()
        self.TEmeta = QTextEdit()
        # cannot edit these
        self.label_rubric_id = QLabel("Will be auto-assigned")
        self.TEuser = QLabel()
        self.TEquestnum = QLabel()

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
        flay.addRow("Rubric ID", self.label_rubric_id)
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
                self.label_rubric_id.setText(str(com["id"]))
            if com["username"]:
                self.TEuser.setText(com["username"])
            if com["question_number"]:
                self.TEquestnum.setText(str(com["question_number"]))
        else:
            self.TE.setPlaceholderText(
                'Prepend with "tex:" to use math.\n\n'
                'You can "choose text" to harvest existing text from the page.\n\n'
                'Change "delta" below to associate a point-change.'
            )
            self.TEmeta.setPlaceholderText(
                "notes to self, hints on when to use this comment, etc.\n\n"
                "Not shown to student!"
            )
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
        self.cb0 = QCheckBox("Hide comments from other questions **recommended**")
        self.cb1 = QCheckBox("Hide comments from other users (except manager)")
        self.cb2 = QCheckBox("Hide comments from manager")
        self.cb3 = QCheckBox("Hide system-comments **recommended**")
        self.cb0.setCheckState(Qt.Checked if curFilters[0] else Qt.Unchecked)
        self.cb1.setCheckState(Qt.Checked if curFilters[1] else Qt.Unchecked)
        self.cb2.setCheckState(Qt.Checked if curFilters[2] else Qt.Unchecked)
        self.cb3.setCheckState(Qt.Checked if curFilters[3] else Qt.Unchecked)
        flay = QVBoxLayout()
        flay.addWidget(self.cb0)
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
            self.cb0.checkState() == Qt.Checked,
            self.cb1.checkState() == Qt.Checked,
            self.cb2.checkState() == Qt.Checked,
            self.cb3.checkState() == Qt.Checked,
        ]


class RubricTable(QTableWidget):
    def __init__(self, parent, sort=False):
        super().__init__()
        self.parent = parent
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Delta", "Text"])
        self.hideColumn(0)
        self.hideColumn(1)
        if sort:
            self.setSortingEnabled(True)
        ##
        self.pressed.connect(self.handleClick)
        # self.itemChanged.connect(self.handleClick)
        self.doubleClicked.connect(self.editRow)

    def contextMenuEvent(self, event):
        log.debug("Popping up a popup menu")
        menu = QMenu(self)
        if True:  # if this_is_share_pane
            hideAction = QAction("Hide", self)
            # hideAction.triggered.connect(lambda: self.hide_the_thingy(event))
        else:
            hideAction = QAction("Remove from pane", self)
        menu.addAction(hideAction)
        menu.addSeparator()
        menu.addAction(QAction("Add to Pane A", self))
        menu.addAction(QAction("Add to Pane B", self))
        menu.addAction(QAction("Add to Pane C", self))
        menu.addAction(QAction("Add to new pane...", self))
        menu.addSeparator()
        if True:  # if this_isnt_mine
            menu.addAction(QAction("Edit a copy...", self))
        else:
            menu.addAction(QAction("Edit...", self))
        menu.addSeparator()
        renameTabAction = QAction("Rename this pane...", self)
        renameTabAction.triggered.connect(self.rename_current_tab)
        menu.addAction(renameTabAction)
        if False:  # e.g., share pane, delta pane renamable?
            renameTabAction.setEnabled(False)
        menu.popup(QCursor.pos())

    def rename_current_tab(self):
        # we want the current tab, not current row
        # TODO: this convoluted access probably indicates this is the wrong place for this function
        n = self.parent.RTW.currentIndex()
        log.debug("current tab is %d", n)
        if n < 0:
            return  # "-1 if there is no current widget"
        # TODO: use a custom dialog
        curname = self.parent.tab_names[n]
        s1, ok1 = QInputDialog.getText(
            self, 'Rename pane "{}"'.format(curname["shortname"]), "Enter short name"
        )
        s2, ok2 = QInputDialog.getText(
            self, 'Rename pane "{}"'.format(curname["shortname"]), "Enter long name"
        )
        if ok1 and ok2:
            self.parent.tab_names[n]["shortname"] = s1
            self.parent.tab_names[n]["longname"] = s2
        self.parent.refreshTabHeaderNames()

    def setRubricsByKeys(self, rubric_list, key_list, legalDown=None, legalUp=None):
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

            rc = self.rowCount()
            self.insertRow(rc)
            self.setItem(rc, 0, QTableWidgetItem(rb["id"]))
            self.setItem(rc, 1, QTableWidgetItem(rb["username"]))
            self.setItem(rc, 2, QTableWidgetItem(rb["delta"]))
            self.setItem(rc, 3, QTableWidgetItem(rb["text"]))
            # set row header
            self.setVerticalHeaderItem(rc, QTableWidgetItem(" {} ".format(rc + 1)))
            # set 'illegal' colour if out of range
            if legalDown is not None and legalUp is not None:
                v = deltaToInt(rb["delta"])
                if v > legalUp or v < legalDown:
                    self.item(rc, 2).setForeground(colour_illegal)
                    self.item(rc, 3).setForeground(colour_illegal)

        self.resizeColumnsToContents()

    def setDeltaRubrics(self, markStyle, maxMark, rubrics):
        """Clear table and repopulate with delta-rubrics"""
        # remove everything
        for r in range(self.rowCount()):
            self.removeRow(0)
        # grab the delta-rubrics from the rubricslist
        delta_rubrics = []
        for rb in rubrics:
            # make sure you get the ones relevant to the marking style
            if rb["username"] == "manager" and rb["meta"] == "delta":
                if markStyle == 2 and int(rb["delta"]) >= 0:
                    delta_rubrics.append(rb)
                if markStyle == 3 and int(rb["delta"]) <= 0:
                    delta_rubrics.append(rb)
        # to make sure the delta is legal, set legalUp,down
        if markStyle == 2:
            legalUp = maxMark
            legalDown = 0
        else:
            legalUp = 0
            legalDown = -maxMark
        # now sort in numerical order away from 0 and add
        for rb in sorted(delta_rubrics, key=lambda r: abs(int(r["delta"]))):
            rc = self.rowCount()
            self.insertRow(rc)
            self.setItem(rc, 0, QTableWidgetItem(rb["id"]))
            self.setItem(rc, 1, QTableWidgetItem(rb["username"]))
            self.setItem(rc, 2, QTableWidgetItem(rb["delta"]))
            self.setItem(rc, 3, QTableWidgetItem(rb["text"]))
            self.setVerticalHeaderItem(rc, QTableWidgetItem(" {} ".format(rc + 1)))
            # set 'illegal' colour if out of range
            if legalDown is not None and legalUp is not None:
                v = int(rb["delta"])
                if v > legalUp or v < legalDown:
                    self.item(rc, 2).setForeground(colour_illegal)
                    self.item(rc, 3).setForeground(colour_illegal)

    def getKeyFromRow(self, row):
        return self.item(r, 0).text()

    def getRowFromKey(self, row):
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
        self.selectRubricByRow(r)

    def selectRubricByRow(self, r):
        """Reset the comment row on a new task to last highlighted comment.

        Args:
            r (int): The row-number in the rubric-table.
            If r is None, do nothing.
        """
        if r is not None:
            self.selectRow(r)

    def selectRubricByKey(self, key):
        """Select row with given key. Return true if works, else false"""
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
                self.selectRubricByRow(0)
            return
        r = (r + 1) % self.rowCount()
        self.selectRubricByRow(r)

    def previousRubric(self):
        """Move selection to the prevoous row, wrapping around if needed."""
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() >= 1:
                self.selectRubricByRow(self.rowCount() - 1)
            return
        r = (r - 1) % self.rowCount()
        self.selectRubricByRow(r)

    def handleClick(self):
        # When an item is clicked, grab the details and emit rubric signal [key, delta, text]
        r = self.getCurrentRubricRow()
        if r is None:
            return
        # recall columns are ["Key", "Username", "Delta", "Text"])
        self.parent.rubricSignal.emit(  # send delta, text, rubricID
            [
                self.item(r, 2).text(),
                self.item(r, 3).text(),
                self.item(r, 0).text(),
            ]
        )

    def updateLegalityOfDeltas(self, legalDown, legalUp):
        """Style items according to legal range of a<=delta<=b"""
        for r in range(self.rowCount()):
            v = deltaToInt(self.item(r, 2).text())
            if v > legalUp or v < legalDown:
                self.item(r, 2).setForeground(colour_illegal)
                self.item(r, 3).setForeground(colour_illegal)
            else:
                self.item(r, 2).setForeground(colour_legal)
                self.item(r, 3).setForeground(colour_legal)

    def editRow(self, tableIndex):
        r = tableIndex.row()
        rubricKey = self.item(r, 0).text()
        self.parent.edit_rubric(rubricKey)


class RubricWidget(QWidget):
    # This is picked up by the annotator and tells is what is
    # the current comment and delta
    rubricSignal = pyqtSignal(list)  # pass the rubric's [key, delta, text]

    def __init__(self, parent):
        # layout the widget - a table and add/delete buttons.
        super(RubricWidget, self).__init__()
        self.test_name = None
        self.question_number = None
        self.tgv = None
        self.parent = parent
        self.username = parent.username
        self.markStyle = 2  # default to mark-up
        self.maxMark = None
        self.currentMark = None
        self.rubrics = None
        # set sensible initial state
        self.wranglerState = None

        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        # TODO: markstyle set after rubric widget added
        # if self.parent.markStyle == 2: ...
        delta_label = "\N{Plus-minus Sign}n"
        # TODO: hardcoded length for now
        self.tab_names = [
            {"shortname": "Shared", "longname": "Shared"},
            {"shortname": "\N{Black Star}", "longname": "Favourites"},
            {"shortname": "A", "longname": None},
            {"shortname": "B", "longname": None},
            {"shortname": delta_label, "longname": "Delta"},
        ]
        self.tabA = RubricTable(self)  # group A
        self.tabB = RubricTable(self)  # group B
        self.tabC = RubricTable(self)  # group C
        self.tabS = RubricTable(self, sort=True)  # Shared
        self.tabDelta = RubricTable(self)  # group C
        self.numberOfTabs = 5
        self.RTW = QTabWidget()
        self.RTW.tabBar().setChangeCurrentOnDrag(True)
        self.RTW.addTab(self.tabS, self.tab_names[0]["shortname"])
        self.RTW.addTab(self.tabA, self.tab_names[1]["shortname"])
        self.RTW.addTab(self.tabB, self.tab_names[2]["shortname"])
        self.RTW.addTab(self.tabC, self.tab_names[3]["shortname"])
        self.RTW.addTab(self.tabDelta, self.tab_names[4]["shortname"])
        self.RTW.setCurrentIndex(0)  # start on shared tab
        grid.addWidget(self.RTW, 1, 1, 2, 4)
        self.addB = QPushButton("Add")
        self.filtB = QPushButton("Arrange/Filter")
        self.otherB = QToolButton()
        self.otherB.setText("\N{Anticlockwise Open Circle Arrow}")
        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.filtB, 3, 2)
        grid.addWidget(self.otherB, 3, 3)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.add_new_rubric)
        self.filtB.clicked.connect(self.wrangleRubrics)
        self.otherB.clicked.connect(self.refreshRubrics)

    def refreshTabHeaderNames(self):
        # TODO: this will fail with movable tabs: probably we need to store this
        # `tab_names` info inside the RubricTables instead of `self.tab_names`.
        print("Note: {} tabs".format(self.RTW.count()))
        for n in range(self.RTW.count()):
            log.debug(
                'refresh tab %d text from "%s" to "%s"',
                n,
                self.RTW.tabText(n),
                self.tab_names[n]["shortname"],
            )
            self.RTW.setTabText(n, self.tab_names[n]["shortname"])

    def refreshRubrics(self):
        """Get rubrics from server and if non-trivial then repopulate"""
        new_rubrics = self.parent.getRubrics()
        if new_rubrics is not None:
            self.rubrics = new_rubrics
            self.wrangleRubrics()
        # do legality of deltas check
        self.updateLegalityOfDeltas()

    def wrangleRubrics(self):
        wr = RubricWrangler(
            self.rubrics, self.wranglerState, self.username, self.tab_names
        )
        if wr.exec_() != QDialog.Accepted:
            return
        else:
            self.wranglerState = wr.wranglerState
            self.setRubricsFromStore()
            # ask annotator to save this stuff back to marker
            self.parent.saveWranglerState()

    def setInitialRubrics(self):
        """Grab rubrics from server and set sensible initial values. Called after annotator knows its tgv etc."""

        self.rubrics = self.parent.getRubrics()
        self.wranglerState = {
            "shown": [],
            "hidden": [],
            "tabs": [[], [], []],
            "hideManager": Qt.Unchecked,
            "hideUsers": Qt.Unchecked,
        }
        # only rubrics for this question
        # exclude other users except manager
        # exclude manager-delta rubrics
        for X in self.rubrics:
            if X["username"] not in [self.username, "manager"]:
                continue
            if X["username"] == "manager" and X["meta"] == "delta":
                continue
            self.wranglerState["shown"].append(X["id"])
        # then set state from this
        self.setRubricsFromStore()

    def setRubricsFromStore(self):
        # if score is x/N then largest legal delta = +(N-x)
        legalUp = self.maxMark - self.currentMark
        # if score is x/N then smallest legal delta = -x
        legalDown = -self.currentMark
        # now change upper/lower bounds depending on marking style
        if self.markStyle == 2:  # mark up
            legalDown = 0
        elif self.markStyle == 3:  # mark down
            legalUp = 0

        self.tabA.setRubricsByKeys(
            self.rubrics,
            self.wranglerState["tabs"][0],
            legalDown=legalDown,
            legalUp=legalUp,
        )
        self.tabB.setRubricsByKeys(
            self.rubrics,
            self.wranglerState["tabs"][1],
            legalDown=legalDown,
            legalUp=legalUp,
        )
        self.tabC.setRubricsByKeys(
            self.rubrics,
            self.wranglerState["tabs"][2],
            legalDown=legalDown,
            legalUp=legalUp,
        )
        self.tabS.setRubricsByKeys(
            self.rubrics,
            self.wranglerState["shown"],
            legalDown=legalDown,
            legalUp=legalUp,
        )
        self.tabDelta.setDeltaRubrics(
            self.markStyle,
            self.maxMark,
            self.rubrics,
        )

    def getCurrentRubricKeyAndTab(self):
        """return the current rubric key and the current tab"""
        return [
            self.RTW.currentWidget().getCurrentRubricKey(),
            self.RTW.currentIndex(),
        ]

    def setCurrentRubricKeyAndTab(self, key, tab):
        """set the current rubric key and the current tab"""
        self.RTW.setCurrentIndex(tab)
        self.RTW.currentWidget().selectRubricByKey(key)

    def setStyle(self, markStyle):
        self.markStyle = markStyle

    def setQuestionNumber(self, qn):
        self.question_number = qn

    def setTestName(self, tn):
        self.test_name = tn

    def reset(self):
        """Return the widget to a no-TGV-specified state."""
        self.setQuestionNumber(None)
        self.setTestName(None)
        print("TODO - what else needs doing on reset")
        # TODO: do we need to do something about maxMark, currentMax, markStyle?
        # self.CL.populateTable()

    def changeMark(self, currentMark, maxMark=None):
        # Update the current and max mark and so recompute which deltas are displayed
        if maxMark:
            self.maxMark = maxMark

        self.currentMark = currentMark
        self.updateLegalityOfDeltas()

    def updateLegalityOfDeltas(self):
        # if score is x/N then largest legal delta = +(N-x)
        legalUp = self.maxMark - self.currentMark
        # if score is x/N then smallest legal delta = -x
        legalDown = -self.currentMark
        # now change upper/lower bounds depending on marking style
        if self.markStyle == 2:  # mark up
            legalDown = 0
        elif self.markStyle == 3:  # mark down
            legalUp = 0
        # now redo each tab
        self.tabA.updateLegalityOfDeltas(legalDown, legalUp)
        self.tabB.updateLegalityOfDeltas(legalDown, legalUp)
        self.tabC.updateLegalityOfDeltas(legalDown, legalUp)
        self.tabS.updateLegalityOfDeltas(legalDown, legalUp)
        self.tabDelta.updateLegalityOfDeltas(legalDown, legalUp)

    def handleClick(self):
        self.RTW.currentWidget().handleClick()

    def reselectCurrentRubric(self):
        self.RTW.currentWidget().reselectCurrentRubric()

    def selectRubricByRow(self, rowNumber):
        self.RTW.currentWidget().selectRubricByRow(rowNumber)
        self.handleClick()

    def nextRubric(self):
        self.RTW.currentWidget().nextRubric()

    def previousRubric(self):
        self.RTW.currentWidget().previousRubric()

    def next_pane(self):
        self.RTW.setCurrentIndex((self.RTW.currentIndex() + 1) % self.numberOfTabs)
        self.handleClick()

    def prev_pane(self):
        self.RTW.setCurrentIndex((self.RTW.currentIndex() - 1) % self.numberOfTabs)
        self.handleClick()

    def get_nonrubric_text_from_page(self):
        """Find any text that isn't already part of a formal rubric.

        Returns:
            list: strings for each text on page that is not inside a rubric
        """
        return self.parent.get_nonrubric_text_from_page()

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
        msg = SimpleMessage(
            "<p>You did not create this message.</p>"
            "<p>To edit it, the system will make a copy that you can edit.</p>"
            "<p>Do you want to continue?</p>"
        )
        if msg.exec_() == QMessageBox.No:
            return
        com = com.copy()  # don't muck-up the original
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
        reapable = self.get_nonrubric_text_from_page()
        arb = AddRubricBox(self.username, self.maxMark, reapable, com)
        if arb.exec_() != QDialog.Accepted:
            return
        if arb.DE.checkState() == Qt.Checked:
            dlt = str(arb.SB.textFromValue(arb.SB.value()))
        else:
            dlt = "."
        txt = arb.TE.toPlainText().strip()
        if len(txt) <= 0:
            return
        tag = arb.TEtag.toPlainText().strip()
        meta = arb.TEmeta.toPlainText().strip()
        username = arb.TEuser.text().strip()
        # only meaningful if we're modifying
        rubricID = arb.label_rubric_id.text().strip()

        new_rubric = {
            "delta": dlt,
            "text": txt,
            "tags": tag,
            "meta": meta,
            "username": self.username,
            "question": self.question_number,
        }

        if edit:
            new_rubric["id"] = rubricID
            rv = self.parent.modifyRubric(rubricID, new_rubric)
            # update the rubric in the current internal rubric list
            # make sure that keys match.
            assert self.rubrics[index]["id"] == new_rubric["id"]
            # then replace
            self.rubrics[index] = new_rubric
        else:
            rv = self.parent.createNewRubric(new_rubric)
            # check was updated/created successfully
            if not rv[0]:  # some sort of creation problem
                return
            # created ok
            rubricID = rv[1]
            new_rubric["id"] = rubricID
            # at this point we have an accepted new rubric
            # add it to the internal list of rubrics
            self.rubrics.append(new_rubric)
            # also add it to the list in the current rubriclist and the shownlist
            # update wranglerState (as if we have run that)
            # then update the displayed rubrics
            self.wranglerState["shown"].append(rubricID)
            if self.RTW.currentIndex() in [0, 1, 2]:
                self.wranglerState["tabs"][self.RTW.currentIndex()].append(rubricID)
        # refresh the rubrics from our internal list
        self.setRubricsFromStore()
        # finally - select that rubric and simulate a click
        self.RTW.currentWidget().selectRubricByKey(rubricID)
        self.handleClick()


class SignedSB(QSpinBox):  # add an explicit sign to spinbox
    def textFromValue(self, n):
        t = QSpinBox().textFromValue(n)
        if n > 0:
            return "+" + t
        else:
            return t


class AddRubricBox(QDialog):
    def __init__(self, username, maxMark, lst, com=None):
        """Initialize a new dialog to edit/create a comment.

        Args:
            username (str)
            maxMark (int)
            lst (list): these are used to "harvest" plain 'ol text
                annotations and morph them into comments.
            com (dict/None): if None, we're creating a new rubric.
                Otherwise, this has the current comment data.
        """
        super().__init__()

        if com:
            self.setWindowTitle("Modify rubric")
        else:
            self.setWindowTitle("Add new rubric")
        self.CB = QComboBox()
        self.TE = QTextEdit()
        self.SB = SignedSB()
        # self.SB = QSpinBox()
        self.DE = QCheckBox("enabled")
        self.DE.setCheckState(Qt.Checked)
        self.DE.stateChanged.connect(self.toggleSB)
        self.TEtag = QTextEdit()
        self.TEmeta = QTextEdit()
        # cannot edit these
        self.label_rubric_id = QLabel("Will be auto-assigned")
        self.TEuser = QLabel()

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
        flay.addRow("Rubric ID", self.label_rubric_id)
        flay.addRow("User who created", self.TEuser)

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
                self.label_rubric_id.setText(str(com["id"]))
            if com["username"]:
                self.TEuser.setText(com["username"])
        else:
            self.TE.setPlaceholderText(
                'Prepend with "tex:" to use math.\n\n'
                'You can "choose text" to harvest existing text from the page.\n\n'
                'Change "delta" below to associate a point-change.'
            )
            self.TEmeta.setPlaceholderText(
                "notes to self, hints on when to use this comment, etc.\n\n"
                "Not shown to student!"
            )
            self.TEuser.setText(username)

    def changedCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.CB.currentText())

    def toggleSB(self):
        if self.DE.checkState() == Qt.Checked:
            self.SB.setEnabled(True)
        else:
            self.SB.setEnabled(False)
