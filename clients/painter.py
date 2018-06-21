import sys
import os
import json

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QGridLayout, QGroupBox, QLabel, QListWidget, QListWidgetItem, QPushButton, QShortcut, QToolButton, QWidget

from pageview import PageView

class SimpleTB(QToolButton):
    def __init__(self, txt, icon):
        super(QToolButton, self).__init__()
        self.setText(txt);
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);
        self.setIcon(QIcon(QPixmap(icon)));
        self.setIconSize(QSize(24,24))
        self.setMinimumWidth(100)

class CommentList(QListWidget):
    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection);
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True);

        self.itemClicked.connect(lambda: self.handleClick())

        self.loadCommentList()

        for txt in self.clist:
            it = QListWidgetItem(txt)
            it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
            self.addItem(it)

    def handleClick(self):
        self.parent().parent().view.setCursor(QCursor(Qt.IBeamCursor))
        self.parent().parent().view.makeComment(self.currentItem().text())

    def loadCommentList(self):
        if(os.path.exists('commentList.json')):
            self.clist = json.load(open('commentList.json'))
        else:
            self.clist = ['algebra', 'arithmetic', 'be careful', 'very nice']

    def saveCommentList(self):
        self.clist=[]
        for r in range(self.count()):
            self.clist.append( self.item(r).text() )

        with open('commentList.json', 'w') as fname:
            json.dump(self.clist, fname)

class CommentWrapper(QWidget):
    def __init__(self,parent):
        QWidget.__init__(self,parent)
        grid = QGridLayout()
        self.CL = CommentList(self)
        grid.addWidget(self.CL, 1, 1, 2, 3)
        self.addB = QPushButton('Add')
        self.addB.clicked.connect(lambda: self.addItem())

        self.delB = QPushButton('Delete')
        self.delB.clicked.connect(lambda: self.deleteItem())

        grid.addWidget(self.addB,3,1)
        grid.addWidget(self.delB,3,3)
        self.setLayout(grid)

    def saveComments(self):
        self.CL.saveCommentList()

    def addItem(self):
        self.CL.setFocus()
        it = QListWidgetItem('EDIT ME')
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        self.CL.addItem(it)
        self.CL.setCurrentItem(it)
        self.CL.editItem(self.CL.currentItem())

    def deleteItem(self):
        self.CL.setFocus()
        self.CL.takeItem(self.CL.currentRow())



class Painter(QDialog):
    def __init__(self, fname, maxMark, parent=None):
        super(Painter, self).__init__(parent)
        self.maxMark=maxMark
        self.currentBackground = "border: 2px solid #008888; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop: 0 #00bbbb, stop: 1 #008888); "
        self.initUI(fname)

    def keyPressEvent(self, event):
        if not event.key() == Qt.Key_Escape:
            super(Painter, self).keyPressEvent(event)

    def setMode(self, newMode, newCursor):
        if( self.previousButton is None):
            pass
        else:
            self.previousButton.setStyleSheet("")
        self.previousButton=self.sender()
        # self.previousButton.setStyleSheet("background-color: #008888; border: 2px solid #00bbbb;")
        self.previousButton.setStyleSheet(self.currentBackground)

        self.view.setMode(newMode)
        self.view.setCursor(newCursor)

    def initUI(self, fname):
        grid = QGridLayout()
        self.imageFile = fname

        self.view = PageView(self, self.imageFile)
        grid.addWidget(self.view, 1,1,12,1)

        self.penB = SimpleTB("&pen", "icons/pen.svg")
        self.penB.setStyleSheet(self.currentBackground) #start in pen mode.
        self.previousButton=self.penB #start in pen mode.
        self.penB.clicked.connect(lambda: self.setMode("pen", QCursor(Qt.ArrowCursor)))

        self.lineB = SimpleTB("&line", "icons/line.svg")
        self.lineB.clicked.connect(lambda: self.setMode("line",QCursor(Qt.CrossCursor)))

        self.crossB = SimpleTB("&xcross", "icons/cross.svg")
        self.crossB.clicked.connect(lambda: self.setMode("cross", QCursor(Qt.ArrowCursor)))

        self.tickB = SimpleTB("&vtick", "icons/tick.svg")
        self.tickB.clicked.connect(lambda: self.setMode("tick", QCursor(Qt.ArrowCursor)))

        self.boxB = SimpleTB("&box", "icons/rectangle.svg")
        self.boxB.clicked.connect(lambda: self.setMode("box", QCursor(Qt.ArrowCursor)))

        self.textB = SimpleTB("&text","icons/text.svg")
        self.textB.clicked.connect(lambda: self.setMode("text", QCursor(Qt.IBeamCursor)))

        self.moveB = SimpleTB("&move", "icons/move.svg")
        self.moveB.clicked.connect(lambda: self.setMode("move", QCursor(Qt.OpenHandCursor)))

        self.deleteB = SimpleTB("&delete", "icons/delete.svg")
        self.deleteB.clicked.connect(lambda: self.setMode("delete", QCursor(Qt.ForbiddenCursor)))

        self.zoomB = SimpleTB("&zoom", "icons/zoom.svg")
        self.zoomB.clicked.connect(lambda: self.setMode("zoom", QCursor(Qt.SizeFDiagCursor)))

        self.panB = SimpleTB("p&an", "icons/pan.svg")
        self.panB.clicked.connect(lambda: ( self.setMode("pan", QCursor(Qt.OpenHandCursor)), self.view.setDragMode(1)) )

        self.undoB = SimpleTB("&undo", "icons/undo.svg")
        self.undoB.clicked.connect(lambda: self.view.undo() )

        self.redoB = SimpleTB("&redo", "icons/redo.svg")
        self.redoB.clicked.connect(lambda: self.view.redo() )

        self.zoomInB = SimpleTB("&in zoom", "icons/zoom_in.svg")
        self.zoomInB.clicked.connect(lambda: self.zoomIn() )

        self.zoomOutB = SimpleTB("&out zoom", "icons/zoom_out.svg")
        self.zoomOutB.clicked.connect(lambda: self.zoomOut() )

        self.gradeBox= QGroupBox()

        self.closeB= QPushButton("&finished")
        self.closeB.clicked.connect(lambda:( self.commentL.saveComments(), self.closeEvent() ))

        self.cancelB= QPushButton("cancel")
        self.cancelB.clicked.connect( lambda: self.reject() )

        grid.addWidget(self.penB,1,2)
        grid.addWidget(self.lineB,1,3)
        grid.addWidget(self.boxB,1,4)
        grid.addWidget(self.textB,2,2)
        grid.addWidget(self.crossB,2,3)
        grid.addWidget(self.tickB,2,4)

        grid.addWidget(self.deleteB,3,2)
        grid.addWidget(self.moveB,3,3)
        grid.addWidget(self.panB,3,4)

        grid.addWidget(self.zoomB,4,2)
        grid.addWidget(self.zoomInB,4,3)
        grid.addWidget(self.zoomOutB,4,4)

        grid.addWidget(self.undoB,5,2)
        grid.addWidget(self.redoB,5,3)

        grid.addWidget(self.closeB,12,2)
        grid.addWidget(self.cancelB,12,4)

        QShortcut(QKeySequence("Ctrl+Z"), self.view, self.view.undo, context=Qt.WidgetShortcut)
        QShortcut(QKeySequence("Ctrl+Shift+z"), self.view, self.view.redo, context=Qt.WidgetShortcut)

        grid.addWidget(self.gradeBox,6,2,1,3)

        gradeGrid=QGridLayout()
        self.gradeCurrentLabel=QLabel("Grade:")
        self.gradeCurrentScore=QLabel("-1")
        gradeGrid.addWidget(self.gradeCurrentLabel,1,1)
        gradeGrid.addWidget(self.gradeCurrentScore,1,2)
        self.gradeButtons = {}
        self.previousGradeButton = None
        for k in range(0, self.maxMark+1):
            self.gradeButtons[k] = QPushButton("{:d}".format(k) )
            self.gradeButtons[k].clicked.connect( lambda:self.gradeSet() )
            gradeGrid.addWidget(self.gradeButtons[k], 2+k//3, k%3)

        self.gradeBox.setLayout(gradeGrid)

        self.commentL=CommentWrapper(self)
        grid.addWidget(self.commentL,7,2,4,3)


        self.setWindowTitle('Annotate Me')
        self.setLayout(grid)
        self.showMaximized()
        self.view.fitInView( self.view.scene.sceneRect(), Qt.KeepAspectRatioByExpanding)
        self.view.centerOn(0,0)


    def gradeSet(self):
        if( self.previousGradeButton is None):
            pass
        else:
            self.previousGradeButton.setStyleSheet("")
        self.previousGradeButton=self.sender()
        self.previousGradeButton.setStyleSheet("border: 2px solid #ff0000; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop: 0 #ff0000, stop: 0.3 #ffaaaa);")

        sender=self.sender()
        self.gradeCurrentScore.setText( sender.text().replace('&','') )
        self.gradeCurrentScore.repaint()
        self.closeB.setFocus()

    def zoomIn(self):
        self.view.scale(1.25,1.25)

    def zoomOut(self):
        self.view.scale(0.8,0.8)

    def closeEvent(self):
        self.view.save()
        self.accept()
