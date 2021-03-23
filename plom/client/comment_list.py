# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Forest Kobayashi

import logging
from pathlib import Path

import toml
import appdirs

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QPalette,
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
    QGroupBox,
    QItemDelegate,
    QMessageBox,
    QMenu,
    QPushButton,
    QToolButton,
    QSpinBox,
    QStackedWidget,
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
from plom.misc_utils import next_in_longest_subsequence
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
# TODO: how do:  QPalette().color(QPalette.Text), QPalette().color(QPalette.Dark)
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
    def __init__(self, parent, shortname=None, sort=False, tabType=None):
        super().__init__()
        self.parent = parent
        self.tabType = tabType  # to help set menu
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(True)
        self.setShowGrid(False)
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
            QTableView::item {
                border: none;
                border-bottom: 1px solid palette(mid);
            }
        """
        )
        # CSS cannot set relative fontsize
        f = self.font()
        f.setPointSizeF(0.67 * f.pointSizeF())
        self.verticalHeader().setFont(f)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Delta", "Text"])
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
        log.debug("tab %s changing name to %s", self.shortname, newname)
        self.shortname = newname
        # TODO: assumes parent is TabWidget, can we do with signals/slots?
        # More like "If anybody cares, I just changed my name!"
        self.parent.update_tab_names()

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
            event.ignore()
        else:
            event.ignore()

    def defaultContextMenuEvent(self, event):
        # first try to get the row from the event
        row = self.rowAt(event.pos().y())
        if row < 0:
            # no row under click but maybe one is highlighted
            row = self.getCurrentRubricRow()
        key = None if row is None else self.getKeyFromRow(row)

        # These are workaround for Issue #1441, lambdas in a loop
        def func_factory_add(t, k):
            def foo():
                t.appendByKey(k)

            return foo

        def func_factory_del(t, k):
            def foo():
                t.removeRubricByKey(k)

            return foo

        menu = QMenu(self)
        if key:
            edit = QAction("Edit rubric", self)
            edit.setEnabled(False)  # TODO hook it up
            menu.addAction(edit)
            menu.addSeparator()

            for tab in self.parent.user_tabs:
                if tab == self:
                    continue
                a = QAction(f"Move to Pane {tab.shortname}", self)
                a.triggered.connect(func_factory_add(tab, key))
                a.triggered.connect(func_factory_del(self, key))
                menu.addAction(a)
            menu.addSeparator()

            remAction = QAction("Remove from this pane", self)
            remAction.triggered.connect(func_factory_del(self, key))
            menu.addAction(remAction)
            menu.addSeparator()

        renameTabAction = QAction("Rename this pane...", self)
        menu.addAction(renameTabAction)
        renameTabAction.triggered.connect(self.rename_current_tab)
        a = QAction("Add new pane", self)
        a.triggered.connect(lambda: self.parent.add_new_tab())
        menu.addAction(a)
        a = QAction("Remove this pane...", self)

        def _local_delete_thyself():
            # TODO: can we put all this in some close event?
            # TODO: I don't like that we're hardcoding the parent structure here
            msg = SimpleMessage(
                f"<p>Are you sure you want to delete the pane &ldquo;{self.shortname}&rdquo;?</p>"
                "<p>(The rubrics themselves will not be deleted).<p>"
            )
            if msg.exec_() == QMessageBox.No:
                return
            for n in range(self.parent.RTW.count()):
                tab = self.parent.RTW.widget(n)
                if tab == self:
                    self.parent.RTW.removeTab(n)
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
        def function_factory(t, k):
            def foo():
                t.appendByKey(k)

            return foo

        menu = QMenu(self)
        if key:
            edit = QAction("Edit rubric", self)
            edit.setEnabled(False)  # TODO hook it up
            menu.addAction(edit)
            menu.addSeparator()

            # TODO: walk in another order for moveable tabs?
            # [self.parent.RTW.widget(n) for n in range(1, 5)]
            for tab in self.parent.user_tabs:
                a = QAction(f"Add to Pane {tab.shortname}", self)
                a.triggered.connect(function_factory(tab, key))
                menu.addAction(a)
            menu.addSeparator()

            hideAction = QAction("Hide", self)
            hideAction.triggered.connect(self.hideCurrentRubric)
            menu.addAction(hideAction)
            menu.addSeparator()
        renameTabAction = QAction("Rename this pane...", self)
        menu.addAction(renameTabAction)
        renameTabAction.triggered.connect(self.rename_current_tab)
        a = QAction("Add new pane", self)
        a.triggered.connect(lambda: self.parent.add_new_tab())
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
        self.selectRubricByRow(0)
        self.handleClick()

    def removeRubricByKey(self, key):
        row = self.getRowFromKey(key)
        if row is None:
            return
        self.removeRow(row)
        self.selectRubricByRow(0)
        self.handleClick()

    def hideCurrentRubric(self):
        row = self.getCurrentRubricRow()
        if row is None:
            return
        key = self.item(row, 0).text()
        self.parent.hideRubricByKey(key)
        self.removeRow(row)
        self.selectRubricByRow(0)
        self.handleClick()

    def unhideCurrentRubric(self):
        row = self.getCurrentRubricRow()
        if row is None:
            return
        key = self.item(row, 0).text()
        self.parent.unhideRubricByKey(key)
        self.removeRow(row)
        self.selectRubricByRow(0)
        self.handleClick()

    def dropEvent(self, event):
        # TODO - simplify - only a single row is selected
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
        curtab_widget = self.parent.RTW.currentWidget()
        if not curtab_widget:
            return
        curname = curtab_widget.shortname
        s1, ok1 = QInputDialog.getText(
            self, 'Rename pane "{}"'.format(curname), "Enter new name"
        )
        if not ok1:
            return
        # TODO: hint that "wh&ot" will enable "alt-o" shortcut on most OSes
        # TODO: use a custom dialog
        # s2, ok2 = QInputDialog.getText(
        #     self, 'Rename pane "{}"'.format(curname), "Enter long name"
        # )
        log.debug('refresh tab text from "%s" to "%s"', curname, s1)
        curtab_widget.set_name(s1)

    def appendByKey(self, key):
        """Append the rubric associated with a key to the end of the list

        If its a dupe, don't add.

        TODO: legalUp/Down stuff?  Not sure I follow.

        args
            key (str/int?): the key associated with a rubric.

        raises
            what happens on invalid key?
        """
        legalDown, legalUp = self.parent.getLegalDownUp()
        # TODO: hmmm, should be dict?
        (rubric,) = [x for x in self.parent.rubrics if x["id"] == key]
        self.appendNewRubric(rubric, legalDown, legalUp)

    def appendNewRubric(self, rubric, legalDown=None, legalUp=None):
        # TODO: why does the caller need to determine this legalUp/Down stuff?
        rc = self.rowCount()
        # do sanity check for duplications
        for r in range(rc):
            if rubric["id"] == self.item(r, 0).text():
                return  # rubric already present
        # is a new rubric, so append it
        self.insertRow(rc)
        self.setItem(rc, 0, QTableWidgetItem(rubric["id"]))
        self.setItem(rc, 1, QTableWidgetItem(rubric["username"]))
        self.setItem(rc, 2, QTableWidgetItem(rubric["delta"]))
        self.setItem(rc, 3, QTableWidgetItem(rubric["text"]))
        # set row header
        self.setVerticalHeaderItem(rc, QTableWidgetItem("{}".format(rc + 1)))
        # set 'illegal' colour if out of range
        if legalDown is not None and legalUp is not None:
            v = deltaToInt(rubric["delta"])
            if v > legalUp or v < legalDown:
                self.item(rc, 2).setForeground(colour_illegal)
                self.item(rc, 3).setForeground(colour_illegal)
            else:
                self.item(rc, 2).setForeground(colour_legal)
                self.item(rc, 3).setForeground(colour_legal)

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

            self.appendNewRubric(rb, legalDown, legalUp)

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
            self.appendNewRubric(rb, legalDown, legalUp)

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
        self.handleClick()

    def previousRubric(self):
        """Move selection to the prevoous row, wrapping around if needed."""
        r = self.getCurrentRubricRow()
        if r is None:
            if self.rowCount() >= 1:
                self.selectRubricByRow(self.rowCount() - 1)
            return
        r = (r - 1) % self.rowCount()
        self.selectRubricByRow(r)
        self.handleClick()

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

    def updateRubric(self, new_rubric, legalDown, legalUp):
        for r in range(self.rowCount()):
            if self.item(r, 0).text() == new_rubric["id"]:
                self.item(r, 1).setText(new_rubric["username"])
                self.item(r, 2).setText(new_rubric["delta"])
                self.item(r, 3).setText(new_rubric["text"])
                # update the legality
                v = deltaToInt(new_rubric["delta"])
                if v > legalUp or v < legalDown:
                    self.item(r, 2).setForeground(colour_illegal)
                    self.item(r, 3).setForeground(colour_illegal)
                else:
                    self.item(r, 2).setForeground(colour_legal)
                    self.item(r, 3).setForeground(colour_legal)


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

        grid = QGridLayout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        delta_label = "\N{Plus-minus Sign}\N{Greek Small Letter Delta}"
        default_user_tabs = ["\N{Black Star}", "\N{Black Heart Suit}"]
        self.tabS = RubricTable(self, shortname="Shared", tabType="show")
        self.tabDelta = RubricTable(self, shortname=delta_label, tabType="delta")
        self.RTW = QTabWidget()
        self.RTW.setMovable(True)
        self.RTW.tabBar().setChangeCurrentOnDrag(True)
        self.RTW.addTab(self.tabS, self.tabS.shortname)
        for name in default_user_tabs:
            tab = RubricTable(self, shortname=name)
            self.RTW.addTab(tab, tab.shortname)
        self.RTW.addTab(self.tabDelta, self.tabDelta.shortname)
        self.RTW.setCurrentIndex(0)  # start on shared tab
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
        self.otherB = QToolButton()
        self.otherB.setText("\N{Anticlockwise Open Circle Arrow}")
        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.filtB, 3, 2)
        grid.addWidget(self.hideB, 3, 3)
        grid.addWidget(self.otherB, 3, 4)
        grid.setSpacing(0)
        self.setLayout(grid)
        # connect the buttons to functions.
        self.addB.clicked.connect(self.add_new_rubric)
        self.filtB.clicked.connect(self.wrangleRubrics)
        self.otherB.clicked.connect(self.refreshRubrics)
        self.hideB.clicked.connect(self.toggleShowHide)

    def toggleShowHide(self):
        if self.showHideW.currentIndex() == 0:  # on main lists
            # move to hidden list
            self.showHideW.setCurrentIndex(1)
            # disable a few buttons
            self.addB.setEnabled(False)
            self.filtB.setEnabled(False)
            self.otherB.setEnabled(False)
            # reselect the current rubric
            self.tabHide.handleClick()
        else:
            # move to main list
            self.showHideW.setCurrentIndex(0)
            # enable buttons
            self.addB.setEnabled(True)
            self.filtB.setEnabled(True)
            self.otherB.setEnabled(True)
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

        If the delta tab is last, insert before that.  Otherwise append
        to the end of tab list.

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
        n = self.RTW.count()
        if n >= 1 and self.RTW.widget(n - 1).is_delta_tab():
            self.RTW.insertTab(n - 1, tab, tab.shortname)
        else:
            self.RTW.addTab(tab, tab.shortname)

    def refreshRubrics(self):
        """Get rubrics from server and if non-trivial then repopulate"""
        new_rubrics = self.parent.getRubrics()
        if new_rubrics is not None:
            self.rubrics = new_rubrics
            self.wrangleRubrics()
        # do legality of deltas check
        self.updateLegalityOfDeltas()

    def wrangleRubrics(self):
        wr = RubricWrangler(self.rubrics, self.get_tab_rubric_lists(), self.username)
        if wr.exec_() != QDialog.Accepted:
            return
        else:
            self.setRubricsFromState(wr.wranglerState)
            # ask annotator to save this stuff back to marker
            self.parent.saveWranglerState(wr.wranglerState)

    def setInitialRubrics(self):
        """Grab rubrics from server and set sensible initial values. Called after annotator knows its tgv etc."""

        self.rubrics = self.parent.getRubrics()
        wranglerState = {
            "user_tab_names": [],
            "shown": [],
            "hidden": [],
            "tabs": [],
        }
        for X in self.rubrics:
            # exclude HALs system-rubrics
            if X["username"] == "HAL":
                continue
            # exclude manager-delta rubrics
            if X["username"] == "manager" and X["meta"] == "delta":
                continue
            wranglerState["shown"].append(X["id"])
        # then set state from this
        self.setRubricsFromState(wranglerState)

    def setRubricsFromState(self, wranglerState):
        """Set rubric tabs (but not rubrics themselves) from saved data.

        The various rubric tabs are updated based on data passed in.
        The rubrics themselves are uneffected.

        args:
            wranglerState (dict): should be documented elsewhere and
                linked here but must contain at least `shown`, `hidden`,
                `tabs`, and `user_tab_names`.  The last two may be empty
                lists.  Subject to change without notice, your milleage
                may vary, etc.

        If there is too much data for the number of data, the extra data
        is discarded.  If there is too few data, pad with empty lists
        and/or leave the current lists as they are.

        TODO: if new Annotator, we may want to clear the tabs before
        calling this.
        """
        # zip truncates shorter list incase of length mismatch
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
        legalDown, legalUp = self.getLegalDownUp()
        for n, tab in enumerate(self.user_tabs):
            if n >= len(wranglerState["tabs"]):
                # not enough data for number of tabs
                idlist = []
            else:
                idlist = wranglerState["tabs"][n]
            tab.setRubricsByKeys(
                self.rubrics,
                idlist,
                legalDown=legalDown,
                legalUp=legalUp,
            )
        self.tabS.setRubricsByKeys(
            self.rubrics,
            wranglerState["shown"],
            legalDown=legalDown,
            legalUp=legalUp,
        )
        self.tabDelta.setDeltaRubrics(
            self.markStyle,
            self.maxMark,
            self.rubrics,
        )
        self.tabHide.setRubricsByKeys(
            self.rubrics,
            wranglerState["hidden"],
            legalDown=legalDown,
            legalUp=legalUp,
        )

        # make sure something selected in each pane
        self.tabHide.selectRubricByRow(0)
        self.tabDelta.selectRubricByRow(0)
        self.tabS.selectRubricByRow(0)
        for tab in self.user_tabs:
            tab.selectRubricByRow(0)

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
        """Adjust to possible changes in marking style between down and up."""
        self.markStyle = markStyle
        if markStyle == 2:
            delta_label = "+\N{Greek Small Letter Delta}"
        elif markStyle == 3:
            delta_label = "-\N{Greek Small Letter Delta}"
        else:
            log.warning("Invalid markstyle specified")
        for n in range(self.RTW.count()):
            if self.RTW.widget(n).is_delta_tab():
                self.RTW.widget(n).shortname = delta_label
                self.RTW.setTabText(n, self.RTW.widget(n).shortname)

    def setQuestionNumber(self, qn):
        """Set question number being graded.

        args:
            qn (int/None): the question number.
        """
        self.question_number = qn

    def setTestName(self, tn):
        self.test_name = tn

    def reset(self):
        """Return the widget to a no-TGV-specified state."""
        self.setQuestionNumber(None)
        self.setTestName(None)
        log.debug("TODO - what else needs doing on reset")
        # TODO: do we need to do something about maxMark, currentMax, markStyle?
        # self.CL.populateTable()

    def changeMark(self, currentMark, maxMark=None):
        # Update the current and max mark and so recompute which deltas are displayed
        if maxMark:
            self.maxMark = maxMark

        self.currentMark = currentMark
        self.updateLegalityOfDeltas()

    def getLegalDownUp(self):
        # if score is x/N then largest legal delta = +(N-x)
        legalUp = self.maxMark - self.currentMark
        # if score is x/N then smallest legal delta = -x
        legalDown = -self.currentMark
        # now change upper/lower bounds depending on marking style
        if self.markStyle == 2:  # mark up
            legalDown = 0
        elif self.markStyle == 3:  # mark down
            legalUp = 0
        return legalDown, legalUp

    def updateLegalityOfDeltas(self):
        legalDown, legalUp = self.getLegalDownUp()
        # now redo each tab
        self.tabS.updateLegalityOfDeltas(legalDown, legalUp)
        self.tabDelta.updateLegalityOfDeltas(legalDown, legalUp)
        for tab in self.user_tabs:
            tab.updateLegalityOfDeltas(legalDown, legalUp)

    def handleClick(self):
        self.RTW.currentWidget().handleClick()

    def reselectCurrentRubric(self):
        self.RTW.currentWidget().reselectCurrentRubric()
        self.handleClick()

    def selectRubricByRow(self, rowNumber):
        self.RTW.currentWidget().selectRubricByRow(rowNumber)
        self.handleClick()

    def nextRubric(self):
        # change rubrics in the right pane
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().nextRubric()
        else:
            self.tabHide.nextRubric()

    def previousRubric(self):
        # change rubrics in the right pane
        if self.showHideW.currentIndex() == 0:
            self.RTW.currentWidget().previousRubric()
        else:
            self.tabHide.previousRubric()

    def next_pane(self):
        # only change panes if they are shown
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            self.RTW.setCurrentIndex((self.RTW.currentIndex() + 1) % numtabs)
            self.handleClick()

    def prev_pane(self):
        # only change panes if they are shown
        if self.showHideW.currentIndex() == 0:
            numtabs = self.RTW.count()
            self.RTW.setCurrentIndex((self.RTW.currentIndex() - 1) % numtabs)
            self.handleClick()

    def get_nonrubric_text_from_page(self):
        """Find any text that isn't already part of a formal rubric.

        Returns:
            list: strings for each text on page that is not inside a rubric
        """
        return self.parent.get_nonrubric_text_from_page()

    def unhideRubricByKey(self, key):
        index = [x["id"] for x in self.rubrics].index(key)
        legalDown, legalUp = self.getLegalDownUp()
        self.tabS.appendNewRubric(self.rubrics[index], legalDown, legalUp)

    def hideRubricByKey(self, key):
        index = [x["id"] for x in self.rubrics].index(key)
        legalDown, legalUp = self.getLegalDownUp()
        self.tabHide.appendNewRubric(self.rubrics[index], legalDown, legalUp)

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
        if self.question_number is None:
            log.error("Not allowed to create rubric while question number undefined.")
            return
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
            # update the rubric in all lists
            self.updateRubricInLists(new_rubric)
        else:
            rv = self.parent.createNewRubric(new_rubric)
            # check was updated/created successfully
            if not rv[0]:  # some sort of creation problem
                return
            # created ok
            rubricID = rv[1]
            new_rubric["id"] = rubricID
            # at this point we have an accepted new rubric
            # compute legaldown/up and add to rubric lists
            legalDown, legalUp = self.getLegalDownUp()
            # add it to the internal list of rubrics
            self.rubrics.append(new_rubric)
            # append the rubric to the shownList
            self.tabS.appendNewRubric(new_rubric, legalDown, legalUp)
            # also add it to the list in the current rubriclist (if different)
            if self.RTW.currentWidget() != self.tabS:
                self.RTW.currentWidget().appendNewRubric(new_rubric, legalDown, legalUp)
        # finally - select that rubric and simulate a click
        self.RTW.currentWidget().selectRubricByKey(rubricID)
        self.handleClick()

    def updateRubricInLists(self, new_rubric):
        legalDown, legalUp = self.getLegalDownUp()
        self.tabS.updateRubric(new_rubric, legalDown, legalUp)
        self.tabHide.updateRubric(new_rubric, legalDown, legalUp)
        for tab in self.user_tabs:
            tab.updateRubric(new_rubric, legalDown, legalUp)

    def get_tab_rubric_lists(self):
        """returns a dict of lists of the current rubrics"""
        return {
            "user_tab_names": [t.shortname for t in self.user_tabs],
            "shown": self.tabS.getKeyList(),
            "hidden": self.tabHide.getKeyList(),
            "tabs": [t.getKeyList() for t in self.user_tabs],
        }


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
