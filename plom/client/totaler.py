__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from collections import defaultdict
import csv
import json
import os
import sys
import tempfile
from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QStringListModel,
    QTimer,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QCompleter, QWidget, QMainWindow, QInputDialog, QMessageBox

from .examviewwindow import ExamViewWindow
import plom.messenger as messenger
from .useful_classes import ErrorMessage, SimpleMessage
from .uiFiles.ui_totaler import Ui_TotalWindow
from plom.plom_exceptions import *
from plom import Plom_API_Version

# set up variables to store paths for marker, id clients and total
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name


class Paper:
    """A simple container for storing a test's idgroup code (tgv) and
    the associated filename for the image. Once identified also
    store the studentName and ID-numer.
    """

    def __init__(self, task, fname, stat="noTotal", mark=""):
        # tgv = t0000p00v0
        # ... = 0123456789
        # The test number
        self.test = task
        # Set status as noTotal
        self.status = stat
        # no total yet
        self.total = mark
        # the filename of the image.
        self.originalFile = fname

    def setStatus(self, st):
        self.status = st

    def setReverted(self):
        # reset the test as nototal and no total
        self.status = "noTotal"
        self.total = ""

    def setTotal(self, val):
        # tgv = t0000p00v0
        # ... = 0123456789
        # Set the test as totaled and store value
        self.status = "totaled"
        self.total = val


class ExamModel(QAbstractTableModel):
    """A tablemodel for handling the test-ID-ing data."""

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        # Data stored in this ordered list.
        self.paperList = []
        # Headers.
        self.header = ["Code", "Status", "Total"]

    def setData(self, index, value, role=Qt.EditRole):
        # Columns are [code, status, Total]
        # Put data in appropriate box when setting.
        if role != Qt.EditRole:
            return False
        if index.column() == 0:
            self.paperList[index.row()].test = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 1:
            self.paperList[index.row()].status = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 2:
            self.paperList[index.row()].total = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def totalPaper(self, index, value):
        # When totaled - set status and total
        self.setData(index[1], "totaled")
        self.setData(index[2], value)

    def revertPaper(self, index):
        # When reverted - set status, ID and Name appropriately.
        self.setData(index[1], "noTotal")
        self.setData(index[2], "")

    def addPaper(self, rho):
        # Append paper to list and update last row of table
        r = self.rowCount()
        self.beginInsertRows(QModelIndex(), r, r)
        self.paperList.append(rho)
        self.endInsertRows()
        return r

    def rowCount(self, parent=None):
        return len(self.paperList)

    def columnCount(self, parent=None):
        return 3

    def data(self, index, role=Qt.DisplayRole):
        # Columns are [code, status, ID and Name]
        # Get data from appropriate box when called.
        if role != Qt.DisplayRole:
            return QVariant()
        elif index.column() == 0:
            return self.paperList[index.row()].test
        elif index.column() == 1:
            return self.paperList[index.row()].status
        elif index.column() == 2:
            return self.paperList[index.row()].total
        return QVariant()

    def headerData(self, c, orientation, role):
        # Return the correct header.
        if role != Qt.DisplayRole:
            return
        elif orientation == Qt.Horizontal:
            return self.header[c]
        return c


# TODO: should be a QMainWindow but at any rate not a QDialog
# TODO: should this be parented by the QApplication?
class TotalClient(QWidget):
    my_shutdown_signal = pyqtSignal(int)

    def __init__(self):
        super(TotalClient, self).__init__()

    def getToWork(self, mess):
        global messenger
        messenger = mess
        # local temp directory for image files and the class list.
        self.workingDirectory = directoryPath
        # List of papers we have to ID.
        self.paperList = []
        self.noTotalCount = 0
        self.maxMark = 0
        # Fire up the interface.
        self.ui = Ui_TotalWindow()
        self.ui.setupUi(self)
        # Paste username into the GUI.
        self.ui.userLabel.setText(messenger.whoami())
        # Exam model for the table of papers - associate to table in GUI.
        self.exM = ExamModel()
        self.ui.tableView.setModel(self.exM)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ExamViewWindow()
        # make sure the resetview is not auto-defaulted to be triggered by return
        self.testImg.resetB.setAutoDefault(False)
        self.ui.gridLayout_7.addWidget(self.testImg, 0, 0)
        # Connect buttons and key-presses to functions.
        self.ui.totalEdit.returnPressed.connect(self.enterTotal)
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.closeButton.setAutoDefault(False)
        self.ui.nextButton.clicked.connect(self.requestNext)
        self.ui.nextButton.setAutoDefault(False)
        # Make sure window is maximised and request a paper from server.
        self.showMaximized()

        # Get the max mark from server
        try:
            self.getMaxMark()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        self.markValidator = QIntValidator(0, self.maxMark)
        self.ui.totalEdit.setValidator(self.markValidator)
        # Get list of papers already ID'd and add to table.
        # Get list of papers already ID'd and add to table.
        try:
            self.getAlreadyTotaledList()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Connect the view **after** list updated.
        # Connect the table's model sel-changed to appropriate function.
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        self.requestNext()
        # make sure exam view window's view is reset....
        # very slight delay to ensure things loaded first
        QTimer.singleShot(100, self.testImg.view.resetView)

    def throwSeriousError(self, err):
        ErrorMessage(
            'A serious error has been thrown:\n"{}".\nCannot recover from this, so shutting down totaller.'.format(
                err
            )
        ).exec_()
        self.shutDownError()
        raise (err)

    def throwBenign(self, err):
        ErrorMessage('A benign exception has been thrown:\n"{}".'.format(err)).exec_()

    def getMaxMark(self):
        """Send request for maximum mark (tGMM) to server. The server then sends
        back the value.
        """
        # Get the classlist from server for name/ID completion.
        self.maxMark = messenger.TgetMaxMark()
        # Update the groupbox label
        self.ui.totalBox.setTitle("Enter total out of {}".format(self.maxMark))

    def shutDownError(self):
        self.my_shutdown_signal.emit(2)
        self.close()

    def shutDown(self):
        """Send the server a DNF (did not finish) message so it knows to
        take anything that this user has out-for-id-ing and return it to
        the todo pile.

        TODO: messenger needs to drop token here?
        """
        self.DNF()
        try:
            messenger.closeUser()
        except PlomSeriousException as err:
            self.throwSeriousError(err)

        self.my_shutdown_signal.emit(2)
        self.close()

    def DNF(self):
        """Send the server a "did not finished" message for each paper
        in the list that has not been totaled. The server will put these back
        onto the todo-pile.
        """
        # Go through each entry in the table - it not ID'd then send a DNF
        # to the server with that paper code.
        rc = self.exM.rowCount()
        for r in range(rc):
            if self.exM.data(self.exM.index(r, 1)) != "totaled":
                try:
                    messenger.TdidNotFinishTask(self.exM.data(self.exM.index(r, 0)))
                except PlomSeriousException as err:
                    self.throwSeriousError(err)

    def getAlreadyTotaledList(self):
        # Ask server for list of previously marked papers
        tList = messenger.TrequestDoneTasks()
        # Add those marked papers to our paper-list
        for x in tList:
            self.addPaperToList(
                Paper(x[0], fname="", stat="totaled", mark=x[2]), update=False
            )

    def selChanged(self, selnew, selold):
        # When the selection changes, update the ID and name line-edit boxes
        # with the data from the table - if it exists.
        # Update the displayed image with that of the newly selected test.
        self.ui.totalEdit.setText(str(self.exM.data(selnew.indexes()[2])))
        self.updateImage(selnew.indexes()[0].row())

    def checkFiles(self, r):
        task = self.exM.paperList[r].test
        # check if we have the image file
        if self.exM.paperList[r].originalFile is not "":
            return
        # else try to grab it from server
        try:
            image = messenger.TrequestImage(task)
        except PlomSeriousException as e:
            self.throwSeriousError(e)
            return
        # save the image to appropriate filename
        fname = os.path.join(self.workingDirectory, "t{}.png".format(task))
        with open(fname, "wb+") as fh:
            fh.write(image)

        self.exM.paperList[r].originalFile = fname

    def updateImage(self, r=0):
        # Here the system should check if imagefile exist and grab if needed.
        self.checkFiles(r)
        # Update the test-image pixmap with the image in the indicated file.
        self.testImg.updateImage(self.exM.paperList[r].originalFile)

    def addPaperToList(self, paper, update=True):
        # Add paper to the exam-table-model - get back the corresponding row.
        r = self.exM.addPaper(paper)
        # select that row and display the image
        if update:
            self.ui.tableView.selectRow(r)
            self.updateImage(r)

    def updateProgress(self):
        # update progressbars
        try:
            v, m = messenger.TprogressCount()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
        if m == 0:
            v, m = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.idProgressBar.setFormat("No papers to total")
            ErrorMessage("No papers to total.").exec_()
        else:
            self.ui.idProgressBar.resetFormat()
        self.ui.idProgressBar.setMaximum(m)
        self.ui.idProgressBar.setValue(v)

    def requestNext(self):
        """Ask the server for an untotaled paper.  Get file, add to the
        list of papers and update the image.
        """
        # update progress bars
        self.updateProgress()

        # ask server for next untotaled paper
        attempts = 0
        while True:
            # TODO - remove this little sanity check else replace with a pop-up warning thingy.
            if attempts >= 5:
                return False
            else:
                attempts += 1
            # ask server for ID of next task
            try:
                test = messenger.TaskNextTask()
                if not test:  # no tasks left
                    return False
            except PlomSeriousException as err:
                self.throwSerious(err)
                return False

            try:
                image = messenger.TclaimThisTask(test)
                break
            except PlomBenignException as err:
                # task already taken.
                continue

        # Image name will be t<code>.png
        iname = os.path.join(self.workingDirectory, "t{}.png".format(test))
        # save it
        with open(iname, "wb+") as fh:
            fh.write(image)

        # Add the paper [code, filename, etc] to the list
        self.addPaperToList(Paper(test, iname))
        # Clean up table - and set focus on the ID-lineedit so user can
        # just start typing in the next ID-number.
        self.ui.tableView.resizeColumnsToContents()
        self.ui.totalEdit.setFocus()

    def totalPaper(self, index, alreadyTotaled=False):
        """User totals the current paper. Some care around whether
        or not the paper was totaled previously. Not called directly - instead
        is called by "entertotal" when user hits return on that lineedit.
        """
        # Pass the contents of the ID-lineedit and Name-lineedit to the exam
        # model to put data into the table.
        self.exM.totalPaper(index, self.ui.totalEdit.text())
        code = self.exM.data(index[0])

        try:
            messenger.TreturnTotaledTask(code, self.ui.totalEdit.text())
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return False

        # Use timer to avoid conflict between completer and
        # clearing the line-edit. Very annoying but this fixes it.
        QTimer.singleShot(0, self.ui.totalEdit.clear)
        # Update progressbars
        self.updateProgress()
        return True

    def moveToNextUntotaled(self):
        # Move to the next test in table which is not totaled.
        rt = self.exM.rowCount()
        if rt == 0:
            return
        rstart = self.ui.tableView.selectedIndexes()[0].row()
        r = (rstart + 1) % rt
        # Be careful to not get stuck in loop if all are totaled.
        while self.exM.data(self.exM.index(r, 1)) == "totaled" and r != rstart:
            r = (r + 1) % rt
        self.ui.tableView.selectRow(r)

    def enterTotal(self):
        """Triggered when user hits return in the total-lineedit.
        """
        # if no papers then simply return.
        if self.exM.rowCount() == 0:
            return
        # Grab table-index and code of current test.
        index = self.ui.tableView.selectedIndexes()
        code = self.exM.data(index[0])
        # No code then return.
        if code is None:
            return
        # Get the status of the test
        status = self.exM.data(index[1])
        alreadyTotaled = False
        # If the paper is already totaled ask the user if they want to
        # change it - set the alreadytotaled flag to true.
        if status == "totaled":
            msg = SimpleMessage("Do you want to change the total?")
            if msg.exec_() == QMessageBox.No:
                return
            else:
                alreadyTotaled = True
        # Check if the entered ID is in the list from the classlist.
        if self.markValidator.validate(self.ui.totalEdit.text(), 0):
            # Ask user to confirm Mark
            msg = SimpleMessage(
                "Total = {}. Enter and move to next?".format(self.ui.totalEdit.text())
            )
            # Put message popup on top-corner of idenfier window
            msg.move(self.pos())
            # If user says "no" then just return from function.
            if msg.exec_() == QMessageBox.No:
                return

        if self.totalPaper(index, alreadyTotaled):
            # if successful, and everything local has been ID'd get next
            if alreadyTotaled is False:
                self.requestNext()
            else:
                # otherwise move to the next unidentified paper.
                self.moveToNextUntotaled()
        return
