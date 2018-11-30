import os
import json

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QGridLayout, QMessageBox, \
    QPushButton, QTableView, QToolButton, QWidget, QItemDelegate


class ErrorMessage(QMessageBox):
    def __init__(self, txt):
        super(ErrorMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class SimpleMessage(QMessageBox):
    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)
        fnt = self.font()
        fnt.setPointSize((fnt.pointSize()*3)//2)
        self.setFont(fnt)


class SimpleTableView(QTableView):
    # This is picked up by the marker, lets it know to annotate
    annotateSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(SimpleTableView, self).__init__()
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.annotateSignal.emit()
        else:
            super(SimpleTableView, self).keyPressEvent(event)


class SimpleToolButton(QToolButton):
    def __init__(self, txt, icon):
        super(SimpleToolButton, self).__init__()
        self.setText(txt)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(QIcon(QPixmap(icon)))
        self.setIconSize(QSize(24, 24))
        self.setMinimumWidth(100)


class CommentWidget(QWidget):
    def __init__(self, parent=None):
        super(CommentWidget, self).__init__()
        grid = QGridLayout()
        self.CL = SimpleCommentTable(self)
        grid.addWidget(self.CL, 1, 1, 2, 3)
        self.addB = QPushButton('Add')
        self.addB.clicked.connect(self.addItem)

        self.delB = QPushButton('Delete')
        self.delB.clicked.connect(self.deleteItem)

        grid.addWidget(self.addB, 3, 1)
        grid.addWidget(self.delB, 3, 3)
        self.setLayout(grid)

    def setStyle(self, markStyle):
        self.CL.delegate.style = markStyle

    def changeMark(self, maxMark, currentMark):
        self.CL.delegate.maxMark = maxMark
        self.CL.delegate.currentMark = currentMark
        self.CL.viewport().update()

    def saveComments(self):
        self.CL.saveCommentList()

    def addItem(self):
        self.CL.addItem()

    def deleteItem(self):
        self.CL.deleteItem()

    def currentItem(self):
        self.CL.currentItem()
        self.setFocus()

    def nextItem(self):
        self.CL.nextItem()
        self.setFocus()

    def previousItem(self):
        self.CL.previousItem()
        self.setFocus()


class commentDelegate(QItemDelegate):
    def __init__(self):
        super(commentDelegate, self).__init__()
        self.currentMark = 0
        self.maxMark = 0
        self.style = 0

    def paint(self, painter, option, index):
        QItemDelegate.paint(self, painter, option, index)
        if index.column() == 0:
            delta = int(index.model().data(index, Qt.EditRole))
            if self.style == 2:  # mark up - disable negative
                if delta <= 0 or delta + self.currentMark > self.maxMark:
                    painter.setBrush(Qt.gray)
                    painter.drawRect(option.rect)
            elif self.style == 3:  # mark down - disable positive
                if delta >= 0 or delta + self.currentMark < 0:
                    painter.setBrush(Qt.gray)
                    painter.drawRect(option.rect)
            if self.style == 1:  # mark total - enable all
                pass


class commentRowModel(QStandardItemModel):
    def dropMimeData(self, data, action, r, c, parent):
        return super().dropMimeData(data, action, r, 0, parent)

    def setData(self, index, value, role=Qt.EditRole):
        # check that data in column zero is numeric
        if index.column() == 0:  # try to convert value to integer
            try:
                v = int(value)  # success! is number
                if v > 0:  # if it is positive, then make sure string is "+v"
                    value = "+{}".format(v)
                # otherwise the current value is "0" or "-n".
            except ValueError:
                value = "0"  # failed, so set to 0.
        # If its column 1 then convert '\n' into actual newline in the string
        elif index.column() == 1:
            value = value.replace('\\n', '\n')
        return super().setData(index, value, role)


class SimpleCommentTable(QTableView):
    # This is picked up by the annotator
    commentSignal = pyqtSignal(list)

    def __init__(self, parent):
        super(SimpleCommentTable, self).__init__()
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragEnabled(True)
        self.setDragDropOverwriteMode(False)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.clicked.connect(self.handleClick)

        self.cmodel = commentRowModel()
        self.cmodel.setHorizontalHeaderLabels(['delta', 'comment'])
        self.setModel(self.cmodel)

        self.delegate = commentDelegate()
        self.setItemDelegate(self.delegate)

        self.clist = []
        self.loadCommentList()
        self.populateTable()
        self.resizeRowsToContents()
        self.resizeColumnToContents(0)
        self.cmodel.itemChanged.connect(self.resizeRowsToContents)

        # set these so that double-click enables edits, but not keypress.
        self.setEditTriggers(QAbstractItemView.NoEditTriggers
                             | QAbstractItemView.DoubleClicked)

    def populateTable(self):
        for (dlt, txt) in self.clist:
            txti = QStandardItem(txt)
            txti.setEditable(True)
            txti.setDropEnabled(False)

            if int(dlt) > 0:
                delti = QStandardItem("+{}".format(int(dlt)))
            else:
                delti = QStandardItem("{}".format(dlt))
            delti.setEditable(True)
            delti.setDropEnabled(False)
            delti.setTextAlignment(Qt.AlignCenter)

            self.cmodel.appendRow([delti, txti])

    def handleClick(self, index=0):
        if index == 0:  # make sure something is selected
            self.currentItem()
        r = self.selectedIndexes()[0].row()
        self.commentSignal.emit([self.cmodel.index(r, 0).data(),
                                 self.cmodel.index(r, 1).data()])

    def loadCommentList(self):
        if os.path.exists('signedCommentList.json'):
            self.clist = json.load(open('signedCommentList.json'))
        else:
            self.clist = [(-1, 'algebra'), (-1, 'arithmetic'), (-1, 'huh?'),
                          (0, 'be careful'),
                          (1, 'good'), (1, 'very nice'), (1, 'yes')]

    def saveCommentList(self):
        self.clist = []
        for r in range(self.cmodel.rowCount()):
            self.clist.append((self.cmodel.index(r, 0).data(),
                               self.cmodel.index(r, 1).data()))
        with open('signedCommentList.json', 'w') as fname:
            json.dump(self.clist, fname)

    def addItem(self):
        txti = QStandardItem("EDIT ME")
        txti.setEditable(True)
        txti.setDropEnabled(False)
        delti = QStandardItem("0")
        delti.setEditable(True)
        delti.setDropEnabled(False)
        delti.setTextAlignment(Qt.AlignCenter)
        self.cmodel.appendRow([delti, txti])
        # select current row
        self.selectRow(self.cmodel.rowCount()-1)
        # fire up editor on the comment which is second selected index
        self.edit(self.selectedIndexes()[1])

    def deleteItem(self):
        sel = self.selectedIndexes()
        if len(sel) == 0:
            return
        self.cmodel.removeRow(sel[0].row())

    def currentItem(self):
        sel = self.selectedIndexes()
        if len(sel) == 0:
            self.selectRow(0)
        else:
            self.selectRow(sel[0].row())

    def nextItem(self):
        sel = self.selectedIndexes()
        if len(sel) == 0:
            self.selectRow(0)
        else:
            self.selectRow((sel[0].row() + 1) % self.cmodel.rowCount())

    def previousItem(self):
        sel = self.selectedIndexes()
        if len(sel) == 0:
            self.selectRow(0)
        else:
            self.selectRow((sel[0].row() - 1) % self.cmodel.rowCount())
