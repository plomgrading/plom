__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai", "Matt Coles"]
__license__ = "GPLv3"

from collections import defaultdict
import csv
import os
import tempfile
from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QStringListModel,
    QTimer,
    QVariant,
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QCompleter, QDialog, QInputDialog, QMessageBox
from examviewwindow import ExamViewWindow
import messenger
from useful_classes import ErrorMessage, SimpleMessage
from uiFiles.ui_totaler import Ui_TotalWindow

# set up variables to store paths for marker, id clients and total
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name


class Paper:
    """A simple container for storing a test's idgroup code (tgv) and
    the associated filename for the image. Once identified also
    store the studentName and ID-numer.
    """

    def __init__(self, tgv, fname):
        # tgv = t0000p00v0
        # ... = 0123456789
        # The test-IDgroup code
        self.prefix = tgv
        # The test number
        self.test = tgv[1:5]
        # Set status as noTotal
        self.status = "noTotal"
        # no total yet
        self.total = ""
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
            self.paperList[index.row()].prefix = value
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
            return self.paperList[index.row()].prefix
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


class TotalClient(QDialog):
    def __init__(self, userName, password, server, message_port, web_port):
        # Init the client with username, password, server and port data.
        super(TotalClient, self).__init__()
        # Init the messenger with server and port data.
        messenger.setServerDetails(server, message_port, web_port)
        messenger.startMessenger()
        # Ping to see if server is up.
        if not messenger.pingTest():
            self.deleteLater()
            return
        # Save username, password, and path the local temp directory for
        # image files and the class list.
        self.userName = userName
        self.password = password
        self.workingDirectory = directoryPath
        # List of papers we have to ID.
        self.paperList = []
        self.noTotalCount = 0
        self.maxMark = 0
        # Fire up the interface.
        self.ui = Ui_TotalWindow()
        self.ui.setupUi(self)
        # Paste username into the GUI.
        self.ui.userLabel.setText(self.userName)
        # Exam model for the table of papers - associate to table in GUI.
        self.exM = ExamModel()
        self.ui.tableView.setModel(self.exM)
        # Connect the table's model sel-changed to appropriate function.
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ExamViewWindow()
        # make sure the resetview is not auto-defaulted to be triggered by return
        self.testImg.resetB.setAutoDefault(False)
        self.ui.gridLayout_7.addWidget(self.testImg, 0, 0)
        # Start using connection to server.
        # Ask server to authenticate user and return the authentication token.
        self.requestToken()
        # Get the max mark from server
        self.getMaxMark()
        self.markValidator = QIntValidator(0, self.maxMark)
        self.ui.totalEdit.setValidator(self.markValidator)
        # Connect buttons and key-presses to functions.
        self.ui.totalEdit.returnPressed.connect(self.enterTotal)
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.closeButton.setAutoDefault(False)
        self.ui.nextButton.clicked.connect(self.requestNext)
        self.ui.nextButton.setAutoDefault(False)
        # Make sure window is maximised and request a paper from server.
        self.showMaximized()
        self.requestNext()

    def requestToken(self):
        """Send authorisation request (AUTH) to server. The request sends name and
        password (over ssl) to the server. If hash of password matches the one
        of file, then the server sends back an "ACK" and an authentication
        token. The token is then used to authenticate future transactions with
        the server (since password hashing is slow).
        """
        # Send and return message with messenger.
        msg = messenger.SRMsg(["AUTH", self.userName, self.password])
        # Return should be [ACK, token]
        # Either a problem or store the resulting token.
        if msg[0] == "ERR":
            ErrorMessage("Password problem")
            quit()
        else:
            self.token = msg[1]

    def getMaxMark(self):
        """Send request for maximum mark (tGMM) to server. The server then sends
        back the value.
        """
        # Send request for classlist (iRCL) to server
        msg = messenger.SRMsg(["tGMM", self.userName, self.token])
        # Return should be [ACK, value]
        if msg[0] == "ERR":
            ErrorMessage("Cannot get maximum mark")
            quit()
        # Get the filename from the message.
        self.maxMark = int(msg[1])
        # Update the groupbox label
        self.ui.totalBox.setTitle("Enter total out of {}".format(self.maxMark))

    def shutDown(self):
        """Send the server a DNF (did not finish) message so it knows to
        take anything that this user has out-for-id-ing and return it to
        the todo pile. Then send a user-closing message so that the
        authorisation token is removed. Then finally close.
        """
        self.DNF()
        msg = messenger.SRMsg(["UCL", self.userName, self.token])
        self.close()

    def DNF(self):
        """Send the server a "did not finished" message for each paper
        in the list that has not been totaled. The server will put these back
        onto the todo-pile.
        """
        # Go through each entry in the table - it not ID'd then send a DNF
        # to the server.
        rc = self.exM.rowCount()
        for r in range(rc):
            if self.exM.data(self.exM.index(r, 1)) != "totaled":
                # Tell user DNF, user, auth-token, and paper's code.
                msg = messenger.SRMsg(
                    [
                        "tDNF",
                        self.userName,
                        self.token,
                        self.exM.data(self.exM.index(r, 0)),
                    ]
                )

    def selChanged(self, selnew, selold):
        # When the selection changes, update the ID and name line-edit boxes
        # with the data from the table - if it exists.
        # Update the displayed image with that of the newly selected test.
        self.ui.totalEdit.setText(self.exM.data(selnew.indexes()[2]))
        self.updateImage(selnew.indexes()[0].row())

    def updateImage(self, r=0):
        # Update the test-image pixmap with the image in the indicated file.
        self.testImg.updateImage(self.exM.paperList[r].originalFile)

    def addPaperToList(self, paper):
        # Add paper to the exam-table-model - get back the corresponding row.
        r = self.exM.addPaper(paper)
        # select that row and display the image
        self.ui.tableView.selectRow(r)
        self.updateImage(r)
        # One more unid'd paper
        self.noTotalCount += 1

    def requestNext(self):
        """Ask the server for an untotaled paper (tNUT). Server should return
        message [ACK, testcode, filename]. Get file from webdav, add to the
        list of papers and update the image.
        """
        # ask server for next unmarked paper
        msg = messenger.SRMsg(["tNUT", self.userName, self.token])
        if msg[0] == "ERR":
            return
        # return message is [ACK, code, filename]
        test = msg[1]
        fname = msg[2]
        # Image name will be <code>.png
        iname = os.path.join(
            self.workingDirectory, test + ".png"
        )  # windows/linux compatibility
        # Grab image from webdav and copy to <code.png>
        messenger.getFileDav(fname, iname)
        # Add the paper [code, filename, etc] to the list
        self.addPaperToList(Paper(test, iname))
        # Tell server we got the image (iGTP) - the server then deletes it.
        msg = messenger.SRMsg(["tGTP", self.userName, self.token, test, fname])
        # Clean up table - and set focus on the ID-lineedit so user can
        # just start typing in the next ID-number.
        self.ui.tableView.resizeColumnsToContents()
        self.ui.totalEdit.setFocus()
        # ask server for id-count update
        msg = messenger.SRMsg(["tPRC", self.userName, self.token])
        # returns [ACK, #id'd, #total]
        if msg[0] == "ACK":
            self.ui.idProgressBar.setValue(msg[1])
            self.ui.idProgressBar.setMaximum(msg[2])

    def totalPaper(self, index, alreadyTotaled=False):
        """User totals the current paper. Some care around whether
        or not the paper was totaled previously. Not called directly - instead
        is called by "entertotal" when user hits return on that lineedit.
        """
        # Pass the contents of the ID-lineedit and Name-lineedit to the exam
        # model to put data into the table.
        self.exM.totalPaper(index, self.ui.totalEdit.text())
        code = self.exM.data(index[0])
        if alreadyTotaled:
            # If the paper was totaled previously send return-already-totaled (tRAT)
            # with the code, ID, name.
            msg = messenger.SRMsg(
                ["tRAT", self.userName, self.token, code, self.ui.totalEdit.text()]
            )
        else:
            # If the paper was not totaled previously send return-previously untotaled (iRUT)
            # with the code, ID, name.
            msg = messenger.SRMsg(
                ["tRUT", self.userName, self.token, code, self.ui.totalEdit.text()]
            )
        if msg[0] == "ERR":
            # If an error, revert the student and clear things.
            self.exM.revertStudent(index)
            # Use timer to avoid conflict between completer and
            # clearing the line-edit. Very annoying but this fixes it.
            QTimer.singleShot(0, self.ui.totalEdit.clear)
            return False
        else:
            # Use timer to avoid conflict between completer and
            # clearing the line-edit. Very annoying but this fixes it.
            QTimer.singleShot(0, self.ui.totalEdit.clear)
            # Update un-id'd count.
            self.noTotalCount -= 1
            return True

    def moveToNextUntotaled(self):
        # Move to the next test in table which is not ID'd.
        rt = self.exM.rowCount()
        if rt == 0:
            return
        rstart = self.ui.tableView.selectedIndexes()[0].row()
        r = (rstart + 1) % rt
        # Be careful to not get stuck in loop if all are ID'd.
        while self.exM.data(self.exM.index(r, 2)) == "totaled" and r != rstart:
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
            # If user says "no" then just return from function.
            if msg.exec_() == QMessageBox.No:
                return

        if self.totalPaper(index, alreadyTotaled):
            # if successful, and everything local has been ID'd get next
            if alreadyTotaled is False and self.noTotalCount == 0:
                self.requestNext()
            else:
                # otherwise move to the next unidentified paper.
                self.moveToNextUntotaled()
        return
