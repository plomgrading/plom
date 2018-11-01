import os
import json

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QCursor, QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QPushButton, QTableView, QToolButton, QWidget, QItemDelegate

class ErrorMessage(QMessageBox):
    def __init__(self, txt):
        super(ErrorMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)

class SimpleMessage(QMessageBox):
    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)
        fnt = self.font()
        fnt.setPointSize((fnt.pointSize()*3)//2)
        self.setFont(fnt)

class SimpleTableView(QTableView):
    annotateSignal = pyqtSignal() #This is picked up by the marker, lets it know to annotate
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

class SimpleCommentList(QListWidget):
    commentSignal = pyqtSignal(['QString']) #This is picked up by the annotator
    def __init__(self, parent):
        super(SimpleCommentList, self).__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.itemClicked.connect(self.handleClick)
        self.loadCommentList()

        for txt in self.clist:
            it = QListWidgetItem(txt)
            it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
            self.addItem(it)

    def handleClick(self):
        self.commentSignal.emit(self.currentItem().text())

    def loadCommentList(self):
        if os.path.exists('commentList.json'):
            self.clist = json.load(open('commentList.json'))
        else:
            self.clist = ['algebra', 'arithmetic', 'be careful', 'very nice']

    def saveCommentList(self):
        self.clist=[]
        for r in range(self.count()):
            self.clist.append( self.item(r).text() )

        with open('commentList.json', 'w') as fname:
            json.dump(self.clist, fname)

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
        print("Changing mark = {} out of {}".format(currentMark, maxMark))

    def saveComments(self):
        self.CL.saveCommentList()

    def addItem(self):
        self.CL.setFocus()
        # it = QListWidgetItem('EDIT ME')
        # it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        # self.CL.addItem(it)
        # self.CL.setCurrentItem(it)
        # self.CL.editItem(self.CL.currentItem())

    def deleteItem(self):
        self.CL.setFocus()
        # self.CL.takeItem(self.CL.currentRow())

    def currentItem(self):
        if self.CL.currentRow() >= 0:
            self.CL.setCurrentRow(self.CL.currentRow())
        else:
            self.CL.setCurrentRow(0)

    def nextItem(self):
        self.CL.setCurrentRow((self.CL.currentRow()+1) % self.CL.count())

    def previousItem(self):
        self.CL.setCurrentRow((self.CL.currentRow()-1) % self.CL.count())


class commentDelegate(QItemDelegate):
    def __init__(self):
        super(commentDelegate, self).__init__()
        self.currentMark = 0
        self.maxMark = 0
        self.style = 0

    def paint(self, painter, option, index):
        if index.column() == 0:
            delta = int(index.model().data(index, Qt.EditRole))
            if self.style == 2:  # mark up - disable negative
                if delta <= 0 or delta + self.currentMark > self.maxMark:
                    painter.setBrush(Qt.red)
                    painter.drawRect(option.rect)
            elif self.style == 3:  # mark down - disable positive
                if delta >= 0 or delta + self.currentMark < 0:
                    painter.setBrush(Qt.red)
                    painter.drawRect(option.rect)
            if self.style == 1:  # mark total - enable all
                pass
        QItemDelegate.paint(self, painter, option, index)

class commentRowModel(QStandardItemModel):
    def dropMimeData(self, data, action, r, c, parent):
        return super().dropMimeData(data, action, r, 0, parent)


class SimpleCommentTable(QTableView):
    commentSignal = pyqtSignal(list) #This is picked up by the annotator
    def __init__(self, parent):
        super(SimpleCommentTable, self).__init__()
        self.verticalHeader().hide()
        self.resizeColumnToContents(0)
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

    def populateTable(self):
        for (dlt, txt) in self.clist:
            txti = QStandardItem(txt)
            txti.setEditable(True)
            txti.setDropEnabled(False)

            if dlt > 0:
                delti = QStandardItem("+{}".format(dlt))
            else:
                delti = QStandardItem("{}".format(dlt))

            delti.setEditable(True)
            delti.setDropEnabled(False)
            self.cmodel.appendRow([delti, txti])

    def handleClick(self, index):
        r = index.row()
        self.commentSignal.emit([self.cmodel.index(r, 0).data(), self.cmodel.index(r, 1).data()])

    def loadCommentList(self):
        if os.path.exists('commentList.json'):
            self.clist = json.load(open('commentList.json'))
        else:
            self.clist = [(-1, 'algebra'), (-1, 'arithmetic'), (0, 'be careful'), (1, 'very nice')]

    def saveCommentList(self):
        self.clist = []
        for r in range(self.count()):
            self.clist.append((self.item(r, 0).text(), self.item(r, 1)))

        with open('commentList.json', 'w') as fname:
            json.dump(self.clist, fname)
