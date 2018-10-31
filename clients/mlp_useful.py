import os
import json

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QCursor, QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QPushButton, QTableView, QToolButton, QWidget

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
    def __init__(self,parent=None):
        super(CommentWidget,self).__init__()
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


class commentRowModel(QStandardItemModel):
    def dropMimeData(self, data, action, r, c, parent):
        return super().dropMimeData(data, action, r, 0, parent)


class SimpleCommentTable(QTableView):
    commentSignal = pyqtSignal(['QString', int]) #This is picked up by the annotator
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

        self.model = commentRowModel()
        self.model.setHorizontalHeaderLabels(['delta', 'comment'])
        self.setModel(self.model)

        self.loadCommentList()

        k=0
        for txt in self.clist:
            k += 1
            txti = QStandardItem(txt)
            txti.setEditable(True)
            txti.setDropEnabled(False)

            delti = QStandardItem(str(k))
            delti.setEditable(True)
            delti.setDropEnabled(False)

            self.model.appendRow([delti, txti])

    def handleClick(self):
        self.commentSignal.emit([self.currentItem().text()])

    def loadCommentList(self):
        if os.path.exists('commentList.json'):
            self.clist = json.load(open('commentList.json'))
        else:
            self.clist = ['algebra', 'arithmetic', 'be careful', 'very nice']
    #
    # def saveCommentList(self):
    #     self.clist=[]
    #     for r in range(self.count()):
    #         self.clist.append( self.item(r).text() )
    #
    #     with open('commentList.json', 'w') as fname:
    #         json.dump(self.clist, fname)
