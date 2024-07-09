# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

from copy import deepcopy
import logging

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QBrush, QColor, QIcon, QImageReader, QPixmap, QTransform
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QListView,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QToolButton,
)

from .useful_classes import WarnMsg, SimpleQuestion
from .viewers import GroupView


log = logging.getLogger("rearrange")


class SourceList(QListWidget):
    """An immutable ordered list of possible pages from the server.

    Some of them may be hidden at any time (e.g., when they are in
    the other Sink List), but they cannot currently be removed or
    added too.  In particular, no changes in the Adjust Pages dialog
    directly make it back to the server.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setAcceptDrops(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setIconSize(QSize(320, 320))
        self.setSpacing(8)
        self.setWrapping(False)
        self.itemDoubleClicked.connect(self.viewImage)
        self.item_positions = {}
        self.item_files = {}
        self.item_orientation = {}
        # self.setSelectionMode(QListView.SelectionMode.SingleSelection)

    def resizeEvent(self, whatev):
        A = self.size()
        x = min(A.width(), A.height())
        # TODO: must be a way to not hardcode 50 here
        # TODO: also compensate for scrollbars or not
        B = QSize(x - 50, x - 50)
        self.setIconSize(B)

    def addImageItem(self, p, pfile, angle, belongs):
        current_row = self.count()
        name = str(p)
        qir = QImageReader(str(pfile))
        # deal with jpeg exif rotations
        qir.setAutoTransform(True)
        pix = QPixmap(qir.read())
        if pix.isNull():
            raise RuntimeError(f"Could not read an image from {pfile}")
        rot = QTransform()
        # 90 means CCW, but we have a minus sign b/c of a y-downward coordsys
        rot.rotate(-angle)
        if angle != 0:
            pix = pix.transformed(rot)
        it = QListWidgetItem(QIcon(pix), name)
        if belongs:
            it.setBackground(QBrush(QColor("darkGreen")))
        self.addItem(it)  # item is added at current_row
        self.item_positions[name] = current_row
        self.item_files[name] = pfile
        self.item_orientation[name] = angle

    def hideItemByName(self, name=None):
        """Removes (hides) a single named item from source-list.

        Returns:
            str: The name of the item we just hid.  If the item was
                already hidden, we still return name here.
        """
        if name is None:
            raise ValueError("You must provide the 'name' argument")

        ci = self.item(self.item_positions[name])

        if ci is None:
            return None
        ci.setHidden(True)
        self.setCurrentItem(None)
        assert ci.text() == name, "Something has gone very wrong: expect match"
        return ci.text()

    def hideSelectedItems(self):
        """Hides the selected items and passes back name list."""
        name_list = []
        for ci in self.selectedItems():
            ci.setHidden(True)
            name_list.append(ci.text())
        self.setCurrentItem(None)
        return name_list

    def unhideNamedItems(self, name_list):
        """Unhide the name list of items."""
        for name in name_list:
            ci = self.item(self.item_positions[name])
            if ci:
                ci.setHidden(False)

    def viewImage(self, qi):
        """Shows a larger view of the currently selected page."""
        self._parent.viewImage(
            [
                {
                    "filename": self.item_files[qi.text()],
                    "orientation": self.item_orientation[qi.text()],
                }
            ]
        )


class SinkList(QListWidget):
    """An ordered list of pages for this task.

    This holds the current view of pages we're considering for this
    task.  They can be reordered, removed (and visually put back in
    the SourceList), rotated, etc.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setAcceptDrops(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setFlow(QListView.Flow.LeftToRight)
        # self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setIconSize(QSize(320, 320))
        self.setSpacing(8)
        self.setWrapping(False)
        # whether or not the item 'officially' belongs to the question
        self.item_belongs = {}
        self.item_files = {}
        self.item_orientation = {}
        self.item_id = {}
        self.itemDoubleClicked.connect(self.viewImage)
        # self.setSelectionMode(QListView.SelectionMode.SingleSelection)

    def resizeEvent(self, whatev):
        A = self.size()
        x = min(A.width(), A.height())
        # TODO: must be a way to not hardcode 50 here
        B = QSize(x - 50, x - 50)
        self.setIconSize(B)

    def addPotentialItem(self, p, pfile, angle, belongs, db_id=None):
        name = str(p)
        self.item_files[name] = pfile
        self.item_orientation[name] = angle
        self.item_id[name] = db_id
        self.item_belongs[name] = belongs

    def removeSelectedItems(self):
        """Remove the selected items and pass back a name list."""
        name_list = []
        # be careful removing things as list indices update as you delete.
        sel_rows = [x.row() for x in self.selectedIndexes()]
        for cr in reversed(sorted(sel_rows)):
            ci = self.takeItem(cr)
            name_list.append(ci.text())

        self.setCurrentItem(None)
        return name_list

    def invert_selection(self):
        selected_indices = [x.row() for x in self.selectedIndexes()]
        for n in range(0, self.count()):
            # self.selectionModel().select(n, QItemSelectionModel.SelectionFlag.Toggle)
            if n in selected_indices:
                self.item(n).setSelected(False)
            else:
                self.item(n).setSelected(True)

    def appendItem(self, name):
        if name is None:
            return
        qir = QImageReader(str(self.item_files[name]))
        # deal with jpeg exif rotations
        qir.setAutoTransform(True)
        pix = QPixmap(qir.read())
        if pix.isNull():
            raise RuntimeError(f"Could not read an image from {self.item_files[name]}")
        ci = QListWidgetItem(QIcon(pix), name)
        if self.item_belongs[name]:
            ci.setBackground(QBrush(QColor("darkGreen")))
        self.addItem(ci)
        # TODO: workaround to force re-orientation on entry to Sink list
        self.rotateForceRefresh(name)
        self.setCurrentItem(ci)

    def appendItems(self, name_list):
        for name in name_list:
            self.appendItem(name)

    def shuffleLeft(self):
        cr = self.currentRow()
        if cr in [-1, 0]:
            return
        ci = self.takeItem(cr)
        self.insertItem(cr - 1, ci)
        self.setCurrentRow(cr - 1)

    def shuffleRight(self):
        cr = self.currentRow()
        if cr in [-1, self.count() - 1]:
            return
        ci = self.takeItem(cr)
        self.insertItem(cr + 1, ci)
        self.setCurrentRow(cr + 1)

    def reverseOrder(self):
        rc = self.count()
        for n in range(rc // 2):
            # swap item[n] with item [rc-n-1]
            ri = self.takeItem(rc - n - 1)
            li = self.takeItem(n)
            self.insertItem(n, ri)
            self.insertItem(rc - n - 1, li)

    def rotateSelectedImages(self, angle=90):
        """Iterate over selection, rotating each image."""
        for i in self.selectedIndexes():
            ci = self.item(i.row())
            name = ci.text()
            self.rotateItemBy(name, angle)
        self._parent.update()
        # Issue #1164 workaround: https://www.qtcentre.org/threads/25867-Problem-with-QListWidget-Updating
        self.setFlow(QListView.Flow.LeftToRight)

    def rotateForceRefresh(self, name):
        """Force an item to visually update its rotate.

        TODO: make this unnecessary and remove it!  Icons should know
        how to display themselves properly.
        """
        angle = self.item_orientation[name]
        if angle == 0:
            return
        log.info("Forcing orientation to %s", format(angle))
        self.rotateItemTo(name, angle)

    def rotateItemBy(self, name: str, delta_angle: int):
        """Rotate image by an angle relative to its current state.

        Args:
            name: name of an image, used as a key.
            delta_angle: rotate by this angle.
        """
        angle = self.item_orientation[name]
        angle = (angle + delta_angle) % 360
        self.rotateItemTo(name, angle)

    def rotateItemTo(self, name: str, angle: int):
        """Rotate image to a particular orientation.

        Args:
            name: name of an image, used as a key.
            angle: rotate to this angle.
        """
        self.item_orientation[name] = angle
        # TODO: instead of loading pixmap again, can we transform the QIcon?
        # Also, docs warned QPixmap.transformed() is slow
        qir = QImageReader(str(self.item_files[name]))
        # deal with jpeg exif rotations
        qir.setAutoTransform(True)
        pix = QPixmap(qir.read())
        if pix.isNull():
            raise RuntimeError(f"Could not read an image from {self.item_files[name]}")
        rot = QTransform()
        # 90 means CCW, but we have a minus sign b/c of a y-downward coordsys
        rot.rotate(-angle)
        if angle != 0:
            pix = pix.transformed(rot)
        # ci = self.item(self.item_positions[name])
        # TODO: instead we get `ci` with a dumb loop
        for i in range(self.count()):
            ci = self.item(i)
            assert ci is not None
            if ci.text() == name:
                break
        assert ci is not None
        ci.setIcon(QIcon(pix))
        # rotpixmap = ci.getIcon().pixmap().transformed(rot)
        # ci.setIcon(QIcon(rotpixmap))

    def viewImage(self, qi):
        """Shows a larger view of the currently selected page."""
        self._parent.viewImage(
            [
                {
                    "filename": self.item_files[qi.text()],
                    "orientation": self.item_orientation[qi.text()],
                }
            ]
        )

    def getNameList(self):
        nList = []
        for r in range(self.count()):
            nList.append(self.item(r).text())
        return nList


class RearrangementViewer(QDialog):
    def __init__(
        self, parent, testNumber, current_pages, page_data, need_to_confirm=False
    ):
        super().__init__(parent)
        self.testNumber = testNumber
        self.need_to_confirm = need_to_confirm
        self._setupUI()
        page_data = self.dedupe_by_md5sum(page_data)
        # stored in an instance variable but only used on reset (and initial setup)
        self.initial_page_data = page_data
        self.nameToIrefNFile = {}
        if current_pages:
            self.populateListWithCurrent(deepcopy(current_pages))
        else:
            self.populateListOriginal()

    def _setupUI(self):
        """Sets up thee UI for the rearrangement Viewer.

        Notes:
             helper method for __init__

        Returns:
            None
        """
        self.scrollA = QScrollArea()
        self.listA = SourceList(self)
        self.listA.itemSelectionChanged.connect(self.show_relevant_tools)
        self.scrollA.setWidget(self.listA)
        self.scrollA.setWidgetResizable(True)
        self.scrollB = QScrollArea()
        self.listB = SinkList(self)
        self.listB.itemSelectionChanged.connect(self.show_relevant_tools)
        self.scrollB.setWidget(self.listB)
        self.scrollB.setWidgetResizable(True)

        self.appendB = QToolButton()
        # TODO: move &A here and use alt-Enter to Accept dialog?
        self.appendB.setText("Add &page(s)")
        self.appendB.setArrowType(Qt.ArrowType.DownArrow)
        self.appendB.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.removeB = QToolButton()
        self.removeB.setArrowType(Qt.ArrowType.UpArrow)
        self.removeB.setText("&Remove page(s)")
        self.removeB.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.sLeftB = QToolButton()
        self.sLeftB.setArrowType(Qt.ArrowType.LeftArrow)
        self.sLeftB.setText("Shift left")
        self.sLeftB.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.sRightB = QToolButton()
        self.sRightB.setArrowType(Qt.ArrowType.RightArrow)
        self.sRightB.setText("Shift right")
        self.sRightB.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.reverseB = QPushButton("Reverse order")
        self.invertSelectionB = QPushButton("Invert selection")
        self.invertSelectionB.clicked.connect(self.invert_selection)
        self.revertB = QPushButton("Revert to original state")
        self.revertB.clicked.connect(self.populateListOriginal)

        self.rotateB_cw = QPushButton("\N{CLOCKWISE OPEN CIRCLE ARROW} Rotate CW")
        self.rotateB_ccw = QPushButton("\N{ANTICLOCKWISE OPEN CIRCLE ARROW} Rotate CCW")

        self.closeB = QPushButton("&Cancel")
        self.acceptB = QPushButton("&Accept")

        self.permute = []

        def GrippyMcGrab():
            """Grippy bars to spice-up QSplitterHandles."""
            width = 64
            pad = 20
            hb = QHBoxLayout()
            hb.addItem(
                QSpacerItem(
                    pad,
                    1,
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Minimum,
                )
            )
            vb = QVBoxLayout()
            hb.addLayout(vb)
            hb.addItem(
                QSpacerItem(
                    pad,
                    1,
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Minimum,
                )
            )

            vb.setContentsMargins(0, 1, 0, 1)
            vb.setSpacing(2)
            vb.addItem(
                QSpacerItem(
                    width,
                    3,
                    QSizePolicy.Policy.MinimumExpanding,
                    QSizePolicy.Policy.MinimumExpanding,
                )
            )
            for i in range(3):
                f = QFrame()
                f.setFrameShape(QFrame.Shape.HLine)
                f.setFrameShadow(QFrame.Shadow.Sunken)
                vb.addWidget(f)
            vb.addItem(
                QSpacerItem(
                    width,
                    3,
                    QSizePolicy.Policy.MinimumExpanding,
                    QSizePolicy.Policy.MinimumExpanding,
                )
            )
            return hb

        hb3 = QHBoxLayout()
        self.tools = QFrame()
        hb = QHBoxLayout()
        self.tools.setLayout(hb)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.addWidget(self.rotateB_ccw)
        hb.addWidget(self.rotateB_cw)
        hb.addSpacing(16)
        hb.addWidget(self.sLeftB)
        hb.addWidget(self.sRightB)
        hb.addSpacing(16)
        hb3.addWidget(self.tools)
        hb3.addWidget(self.reverseB)
        hb3.addSpacing(16)
        hb3.addWidget(self.invertSelectionB)
        hb3.addSpacing(16)
        hb3.addStretch()
        hb3.addWidget(self.acceptB)
        hb3.addWidget(self.closeB)

        allPages = QLabel("Other Pages in Exam")
        thisQuestion = QLabel("Pages for this Question")

        # center add/remove buttons on label row
        hb1 = QHBoxLayout()
        hb1.addWidget(thisQuestion)
        hb1.addLayout(GrippyMcGrab())
        hb = QHBoxLayout()
        hb.addWidget(self.appendB)
        hb.addSpacing(16)
        hb.addStretch()
        hb.addWidget(self.removeB)
        hb1.addLayout(hb)
        hb1.addLayout(GrippyMcGrab())
        hb1.addWidget(self.revertB)

        vb0 = QVBoxLayout()
        s = QSplitter()
        s.setOrientation(Qt.Orientation.Vertical)
        # s.setOpaqueResize(False)
        s.setChildrenCollapsible(False)
        # TODO: better not to hardcode, take from children?
        s.setHandleWidth(50)
        vb0.addWidget(s)
        f = QFrame()
        s.addWidget(f)
        vb = QVBoxLayout()
        vb.setContentsMargins(0, 0, 0, 0)
        f.setLayout(vb)
        vb.addWidget(allPages)
        vb.addWidget(self.scrollA)
        f = QFrame()
        s.addWidget(f)
        vb = QVBoxLayout()
        vb.setContentsMargins(0, 0, 0, 0)
        f.setLayout(vb)
        vb.addWidget(self.scrollB)
        vb.addLayout(hb3)

        handle = s.handle(1)
        vb = QVBoxLayout()
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)
        handle.setLayout(hb1)
        hb1.setContentsMargins(0, 0, 0, 0)
        # TODO: Buttons inside the splitter bar, disable drag and custom cursor
        for b in (self.removeB, self.appendB, self.revertB):
            b.mouseMoveEvent = lambda *args: None
            b.setCursor(Qt.CursorShape.ArrowCursor)

        self.setLayout(vb0)
        self.resize(
            QSize(
                int(self.parent().width() * 7 / 8),
                int(self.parent().height() * 11 / 12),
            )
        )

        self.closeB.clicked.connect(self.close)
        self.sLeftB.clicked.connect(self.shuffleLeft)
        self.sRightB.clicked.connect(self.shuffleRight)
        self.reverseB.clicked.connect(self.reverseOrder)
        self.rotateB_cw.clicked.connect(lambda: self.rotateImages(-90))
        self.rotateB_ccw.clicked.connect(lambda: self.rotateImages(90))
        self.appendB.clicked.connect(self.sourceToSink)
        self.removeB.clicked.connect(self.sinkToSource)
        self.acceptB.clicked.connect(self.doShuffle)

        allPageWidgets = [self.listA, self.listB]

        self.listA.selectionModel().selectionChanged.connect(
            lambda sel, unsel: self.singleSelect(self.listA, allPageWidgets)
        )
        self.listB.selectionModel().selectionChanged.connect(
            lambda sel, unsel: self.singleSelect(self.listB, allPageWidgets)
        )

    def dedupe_by_md5sum(self, page_data):
        """Collapse entries in the pagedata with duplicated md5sums.

        Pages are shared between questions but we only want to show one
        copy of each such duplicated page in the "Adjust pages" dialog.

        The `page_data` is a list of dicts, each with keys `"pagename"`,
        `"md5"`, `"included"`, `"order"`, `"id"`, `"filename"`, and
        others (`"orientation"`, etc) not shown here.  These have
        corresponding values like in the example below.  We want to
        compress rows that have duplicated md5sums:
        ```
        ['h1.1', 'e224c22eda93456143fbac94beb0ffbd', True, 1, 40, '/tmp/plom_zq/tmpnqq.image]
        ['h1.2', '97521f4122df24ca012a12930391195a', True, 2, 41, '/tmp/plom_zq/tmp_om.image]
        ['h2.1', 'e224c22eda93456143fbac94beb0ffbd', False, 1, 40, '/tmp/plom_zq/tmpx0s.image]
        ['h2.2', '97521f4122df24ca012a12930391195a', False, 2, 41, '/tmp/plom_zq/tmpd5g.image]
        ['h2.3', 'abcd1234abcd12314717621412412444', False, 3, 42, '/tmp/plom_zq/tmp012.image]
        ['h3.1', 'abcd1234abcd12314717621412412444', False, 1, 42, '/tmp/plom_zq/tmp012.image]
        ```
        (Possibly filenames are repeated for repeat md5: not required by this code.)

        From this we want something like:
        ```
        ['h1.1 (& h2.1)', 'e224c22eda93456143fbac94beb0ffbd', True, 1, 40, '/tmp/plom_zq/tmpnqq.image]
        ['h1.2 (& h2.2)', '97521f4122df24ca012a12930391195a', True, 2, 41, '/tmp/plom_zq/tmp_om.image]
        ['h2.3 (& h3.1)', 'abcd1234abcd12314717621412412444', False, 3, 42, '/tmp/plom_zq/tmp012.image]
        ```
        where the names of duplicates are shown in parentheses.

        It seems we need to keep the order as much as possible in this file, which complicates this.
        May not be completely well-posed.  Probably better to refactor before this.  E.g., factor out
        a dict of md5sum to filenames before we get here.

        `"included"` (column 3): server said these were ORIGINALLY included
        in this question.  User might have changed this; see "current"
        elsewhere.

        TODO: if order does not have `h1,1` first, should we move it first?
              that is, before the parenthetical?  Probably by re-ordering
              the list.
        """
        # List of lists, preserving original order within each list
        tmp_data = []
        for row in page_data:
            md5s_so_far = [y[0]["md5"] for y in tmp_data]
            if row["md5"] in md5s_so_far:
                i = md5s_so_far.index(row["md5"])
                tmp_data[i].append(row.copy())
            else:
                tmp_data.append([row.copy()])

        def pack_names(names):
            """List of names, abbreviated if list is long."""
            if len(names) < 4:
                s = ", ".join(names)
            else:
                s = ", ".join(names[:2])
                s += f", {len(names) - 2} others"
            return f" (& {s})"

        # Compress each list down to a single item, packing the names
        new_page_data = []
        # warn/log if True not in first?
        for y in tmp_data:
            z = y[0].copy()
            other_names = [_["pagename"] for _ in y[1:]]
            if other_names:
                z["pagename"] = z["pagename"] + pack_names(other_names)
            # If any entry had True for "included", include this row
            # Rearranger uses this to colour pages (originally) included
            z["included"] = any([_["included"] for _ in y])
            new_page_data.append(z)

        return new_page_data

    def show_relevant_tools(self):
        """Hide/show tools based on current selections."""
        if self.listB.selectionModel().hasSelection():
            self.removeB.setEnabled(True)
            self.tools.setEnabled(True)
        else:
            self.removeB.setEnabled(False)
            self.tools.setEnabled(False)
        if self.listA.selectionModel().hasSelection():
            self.appendB.setEnabled(True)
        else:
            self.appendB.setEnabled(False)

    def populateListOriginal(self):
        """Populates the QListWidgets with exam pages, using original server view.

        Returns:
            None: but changes the state of self.
        """
        self.nameToIrefNFile = {}
        self.listA.clear()
        self.listB.clear()
        move_order = {}
        for row in self.initial_page_data:
            self.nameToIrefNFile[row["pagename"]] = row
            # add every page image to list A
            self.listA.addImageItem(
                row["pagename"],
                row["filename"],
                row["orientation"],
                row["included"],
            )
            # add the potential for every page to listB
            self.listB.addPotentialItem(
                row["pagename"],
                row["filename"],
                row["orientation"],
                row["included"],
                db_id=row["id"],
            )
            # if position in current annot is non-null then add to list of pages to move between lists.
            if row["included"] and row["order"]:
                move_order[row["order"]] = row["pagename"]
        for k in sorted(move_order.keys()):
            self.listB.appendItem(self.listA.hideItemByName(name=move_order[k]))

    def populateListWithCurrent(self, current):
        """Populates the QListWidgets with pages, with current state highlighted.

        Args:
            current (list): dicts with 'md5' and 'orientation' keys.

        Returns:
            None: but changes the state of self.
        """
        self.nameToIrefNFile = {}
        self.listA.clear()
        self.listB.clear()
        for row in self.initial_page_data:
            self.nameToIrefNFile[row["pagename"]] = row
            # add every page image to list A
            self.listA.addImageItem(
                row["pagename"],
                row["filename"],
                row["orientation"],
                row["included"],
            )
            # add the potential for every page to listB
            self.listB.addPotentialItem(
                row["pagename"],
                row["filename"],
                row["orientation"],
                row["included"],
                db_id=row["id"],
            )
        for kv in current:
            match = [
                row["pagename"]
                for row in self.initial_page_data
                if row["md5"] == kv["md5"]
            ]
            assert len(match) == 1, "Oops, expected unique md5s in filtered pagedata"
            (match,) = match
            self.listB.appendItem(self.listA.hideItemByName(match))
            self.listB.rotateItemTo(match, kv["orientation"])

    def sourceToSink(self):
        """Adds the currently selected page to the list for the current question.

        Notes:
            If currently selected page is in current question, does nothing.

        Returns:
            None

        """
        if not self.listA.selectionModel().hasSelection():
            return
        self.listB.appendItems(self.listA.hideSelectedItems())

    def sinkToSource(self):
        """Removes the currently selected pages from the list for the current question.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if not self.listB.selectionModel().hasSelection():
            return
        self.listA.unhideNamedItems(self.listB.removeSelectedItems())

    def _sinkInvToSource(self):
        """Removes all pages NOT currently selected from the list for the current question.

        Currently unused as not connected to any buttons.
        """
        self.invert_selection()
        self.sinkToSource()

    def shuffleLeft(self):
        """Shuffles currently selected page to the left one position.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if self.listB.selectionModel().hasSelection():
            self.listB.shuffleLeft()
        else:
            pass

    def shuffleRight(self):
        """Shuffles currently selected page to the left one position.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if self.listB.selectionModel().hasSelection():
            self.listB.shuffleRight()
        else:
            pass

    def reverseOrder(self):
        """Reverses the order of the pages in current question."""
        self.listB.reverseOrder()

    def invert_selection(self):
        """Invert the selection of the bottom list."""
        self.listB.invert_selection()

    def rotateImages(self, angle=90):
        """Rotates the currently selected page, by default by 90 degrees CCW."""
        self.listB.rotateSelectedImages(angle)

    def viewImage(self, image_data):
        """Shows a larger view of one or more pages."""
        GroupView(self, image_data, bigger=True).exec()

    def doShuffle(self):
        """Reorders and saves pages according to user's selections.

        Returns:
            Doesn't return anything directly but sets `permute` instance
            variable which contains a list of dicts, the "page data"
            for the pages the user chose, possibly with new orientation.
        """
        if self.listB.count() == 0:
            msg = "You must have at least one page in the bottom list."
            WarnMsg(self, msg).exec()
            return
        if self.need_to_confirm:
            msg = SimpleQuestion(
                self,
                "This will erase all your annotations.",
                "Are you sure you want to save this page order?",
            )
            if msg.exec() == QMessageBox.StandardButton.No:
                return

        self.permute = []
        for n in self.listB.getNameList():
            row = self.nameToIrefNFile[n]
            assert row["id"] == self.listB.item_id[n], "something we did not foresee!"
            row["orientation"] = self.listB.item_orientation[n]
            self.permute.append(row)
        self.accept()

    def singleSelect(self, currentList, allPages):
        """If item selected by user isn't in currentList, deselects currentList.

        Args:
            currentList (QListWidget): the list being checked.
            allPages (List[QListWidget]): all lists in selection

        Notes:
            from https://stackoverflow.com/questions/45509496/qt-multiple-qlistwidgets-and-only-a-single-entry-selected

        Returns:
            None
        """
        for lstViewI in allPages:
            if lstViewI == currentList:
                continue
            # the check is necessary to prevent recursions...
            if lstViewI.selectionModel().hasSelection():
                # ...as this causes emission of selectionChanged() signal as well:
                lstViewI.selectionModel().clearSelection()
