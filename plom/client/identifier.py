# -*- coding: utf-8 -*-

"""
Identifier Tool
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer, Colin B. Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import csv
import json
import os
import sys
import tempfile
import logging

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
from PyQt5.QtWidgets import (
    QCompleter,
    QDialog,
    QWidget,
    QMainWindow,
    QInputDialog,
    QMessageBox,
)

from .examviewwindow import ExamViewWindow
from .useful_classes import ErrorMessage, SimpleMessage, BlankIDBox, SNIDBox
from .uiFiles.ui_identify import Ui_IdentifyWindow
from .origscanviewer import WholeTestView

from plom.plom_exceptions import *
from plom import Plom_API_Version
from plom import isValidStudentNumber
from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

log = logging.getLogger("identr")

# set up variables to store paths for marker and id clients
tempDirectory = tempfile.TemporaryDirectory(prefix="plom_")
directoryPath = tempDirectory.name


class Paper:
    """A simple container for storing a test's idgroup code (tgv) and
    the associated filename for the image. Once identified also
    store the studentName and ID-numer.
    """

    def __init__(self, test, fnames=[], stat="unidentified", id="", name=""):
        # tgv = t0000p00v0
        # ... = 0123456789
        # The test number
        self.test = test
        # Set status as unid'd
        self.status = stat
        # no name or id-number yet.
        self.sname = name
        self.sid = id
        # the list filenames of the images.
        self.originalFiles = fnames

    def setStatus(self, st):
        self.status = st

    def setReverted(self):
        # reset the test as unidentified and no ID or name.
        self.status = "unidentified"
        self.sid = ""
        self.sname = ""

    def setID(self, sid, sname):
        # tgv = t0000p00v0
        # ... = 0123456789
        # Set the test as ID'd and store name / number.
        self.status = "identified"
        self.sid = sid
        self.sname = sname


class ExamModel(QAbstractTableModel):
    """A tablemodel for handling the test-ID-ing data."""

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        # Data stored in this ordered list.
        self.paperList = []
        # Headers.
        self.header = ["Test", "Status", "ID", "Name"]

    def setData(self, index, value, role=Qt.EditRole):
        # Columns are [code, status, ID and Name]
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
            self.paperList[index.row()].sid = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 3:
            self.paperList[index.row()].sname = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def identifyStudent(self, index, sid, sname):
        # When ID'd - set status, ID and Name.
        self.setData(index[1], "identified")
        self.setData(index[2], sid)
        self.setData(index[3], sname)

    def revertStudent(self, index):
        # When reverted - set status, ID and Name appropriately.
        self.setData(index[1], "unidentified")
        self.setData(index[2], "")
        self.setData(index[3], "")

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
        return 4

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
            return self.paperList[index.row()].sid
        elif index.column() == 3:
            return self.paperList[index.row()].sname
        return QVariant()

    def headerData(self, c, orientation, role):
        # Return the correct header.
        if role != Qt.DisplayRole:
            return
        elif orientation == Qt.Horizontal:
            return self.header[c]
        return c


# TODO: should be a QMainWindow but at any rate not a Dialog
# TODO: should this be parented by the QApplication?
class IDClient(QWidget):
    my_shutdown_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()

    def getToWork(self, mess):
        global messenger
        messenger = mess
        # Save the local temp directory for image files and the class list.
        self.workingDirectory = directoryPath
        # List of papers we have to ID.
        self.paperList = []
        # Fire up the interface.
        self.ui = Ui_IdentifyWindow()
        self.ui.setupUi(self)
        # Paste username into the GUI (TODO: but why?)
        self.ui.userLabel.setText(mess.whoami())
        # Exam model for the table of papers - associate to table in GUI.
        self.exM = ExamModel()
        self.ui.tableView.setModel(self.exM)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ExamViewWindow()
        self.ui.gridLayout_7.addWidget(self.testImg, 0, 0)

        # Get the classlist from server for name/ID completion.
        try:
            self.getClassList()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Init the name/ID completers and a validator for ID
        self.setCompleters()
        # Get the predicted list from server for ID guesses.
        try:
            self.getPredictions()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Connect buttons and key-presses to functions.
        self.ui.idEdit.returnPressed.connect(self.enterID)
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.nextButton.clicked.connect(self.skipOnClick)
        self.ui.predButton.clicked.connect(self.acceptPrediction)
        self.ui.blankButton.clicked.connect(self.blankPaper)
        self.ui.viewButton.clicked.connect(self.viewWholePaper)

        # Make sure no button is clicked by a return-press
        self.ui.nextButton.setAutoDefault(False)
        self.ui.closeButton.setAutoDefault(False)

        # Make sure window is maximised and request a paper from server.
        self.showMaximized()
        # Get list of papers already ID'd and add to table.
        try:
            self.getAlreadyIDList()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Connect the view **after** list updated.
        # Connect the table's model sel-changed to appropriate function.
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        self.requestNext()
        # make sure exam view window's view is reset....
        self.testImg.forceRedrawOrSomeBullshit()
        # Create variable to store ID/Name conf window position
        # Initially set to top-left corner of window
        self.msgGeometry = None

    def throwSeriousError(self, err):
        ErrorMessage(
            'A serious error has been thrown:\n"{}".\nCannot recover from this, so shutting down identifier.'.format(
                err
            )
        ).exec_()
        self.shutDownError()
        raise (err)

    def throwBenign(self, err):
        ErrorMessage('A benign exception has been thrown:\n"{}".'.format(err)).exec_()

    def skipOnClick(self):
        """Skip the current, moving to the next or loading a new one"""
        index = self.ui.tableView.selectedIndexes()
        if len(index) == 0:
            return
        r = index[0].row()  # which row is selected
        if r == self.exM.rowCount() - 1:  # the last row is selected.
            if self.requestNext():
                return
        self.moveToNextUnID()

    def getClassList(self):
        """Get the classlist from the server.

        Returns nothing but modifies the state of self, adding two
        dicts to the class data:

        `student_id_to_name_map`
            Maps unique ID (str) to name (str).

        `student_name_to_idlist`
            Names are not unique so we map each name to a list of IDs.
        """
        # a list of pairs [sid, sname]
        self.student_id_and_name_list = messenger.IDrequestClasslist()
        # use 'snid' to mean "student_id_and_name" as one string.
        self.snid_to_student_id = dict()
        self.snid_to_student_name = dict()
        # also need id to snid for predictionlist wrangling.
        self.student_id_to_snid = dict()

        name_list = []
        for sid, sname in self.student_id_and_name_list:
            snid = "{}: {}".format(sid, sname)
            self.snid_to_student_id[snid] = sid
            self.snid_to_student_name[snid] = sname
            self.student_id_to_snid[sid] = snid

            if sname in name_list:
                log.warning(
                    'Just FYI: multiple students with name "%s"', censorName(sname)
                )

    def getPredictions(self):
        """Send request for prediction list (iRPL) to server. The server then sends
        back the CSV of the predictions testnumber -> studentID.
        """
        # Send request for prediction list to server
        csvfile = messenger.IDrequestPredictions()

        # create dictionary from the prediction list
        self.predictedTestToNumbers = defaultdict(int)
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        for row in reader:
            self.predictedTestToNumbers[int(row["test"])] = str(row["id"])

        # Also tweak font size
        fnt = self.font()
        fnt.setPointSize(fnt.pointSize() * 2)
        self.ui.pNameLabel.setFont(fnt)
        # also tweak size of "accept prediction" button font
        self.ui.predButton.setFont(fnt)
        # make the SID larger still.
        fnt.setPointSize(fnt.pointSize() * 1.5)
        self.ui.pSIDLabel.setFont(fnt)
        # And if no predictions then hide that box
        if len(self.predictedTestToNumbers) == 0:
            self.ui.predictionBox.hide()

        return True

    def setCompleters(self):
        """Set up the studentname + studentnumber line-edit completers.
        Means that user can enter the first few numbers (or letters) and
        be prompted with little pop-up with list of possible completions.
        """
        # Build stringlistmodels - one for combined student_name_and_id = snid
        self.snidlist = QStringListModel()
        # Feed in the numbers and names.
        self.snidlist.setStringList(list(self.snid_to_student_id.keys()))
        # Build the snid-completer = substring matching and case insensitive
        self.snidcompleter = QCompleter()
        self.snidcompleter.setModel(self.snidlist)
        self.snidcompleter.setCaseSensitivity(Qt.CaseInsensitive)
        self.snidcompleter.setFilterMode(Qt.MatchContains)
        # Link the ID-completer to the ID-lineedit in the gui.
        self.ui.idEdit.setCompleter(self.snidcompleter)
        # Make sure lineedit has little "Clear this" button.
        self.ui.idEdit.setClearButtonEnabled(True)

    def shutDownError(self):
        self.my_shutdown_signal.emit(1)
        self.close()

    def shutDown(self):
        """Send the server a DNF (did not finish) message so it knows to
        take anything that this user has out-for-id-ing and return it to
        the todo pile. Then send a user-closing message so that the
        authorisation token is removed. Then finally close.
        TODO: messenger needs to drop token here?
        """
        self.DNF()
        try:
            messenger.closeUser()
        except PlomSeriousException as err:
            self.throwSeriousError(err)

        self.my_shutdown_signal.emit(1)
        self.close()

    def DNF(self):
        """Send the server a "did not finished" message for each paper
        in the list that has not been ID'd. The server will put these back
        onto the todo-pile.
        """
        # Go through each entry in the table - it not ID'd then send a DNF
        # to the server.
        rc = self.exM.rowCount()
        for r in range(rc):
            if self.exM.data(self.exM.index(r, 1)) != "identified":
                # Tell user DNF, user, auth-token, and paper's code.
                try:
                    messenger.IDdidNotFinishTask(self.exM.data(self.exM.index(r, 0)))
                except PlomSeriousException as err:
                    self.throwSeriousError(err)

    def getAlreadyIDList(self):
        # Ask server for list of previously ID'd papers
        idList = messenger.IDrequestDoneTasks()
        for x in idList:
            self.addPaperToList(
                Paper(x[0], fnames=[], stat="identified", id=x[1], name=x[2]),
                update=False,
            )

    def selChanged(self, selnew, selold):
        # When the selection changes, update the ID and name line-edit boxes
        # with the data from the table - if it exists.
        # Update the displayed image with that of the newly selected test.
        self.ui.idEdit.setText(self.exM.data(selnew.indexes()[2]))
        self.updateImage(selnew.indexes()[0].row())
        self.ui.idEdit.setFocus()

    def checkFiles(self, r):
        # grab the selected tgv
        test = self.exM.paperList[r].test
        # check if we have a copy
        if len(self.exM.paperList[r].originalFiles) > 0:
            return
        # else try to grab it from server
        try:
            imageList = messenger.IDrequestImage(test)
        except PlomSeriousException as e:
            self.throwSeriousError(e)
            return
        except PlomBenignException as e:
            self.throwBenign(e)
            # self.exM.removePaper(r)
            return

        # Image names = "i<testnumber>.<imagenumber>.<ext>"
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(self.workingDirectory, "i{}.{}.image".format(test, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])

        self.exM.paperList[r].originalFiles = inames

    def updateImage(self, r=0):
        # Here the system should check if imagefile exist and grab if needed.
        self.checkFiles(r)
        # Update the test-image pixmap with the image in the indicated file.
        self.testImg.updateImage(self.exM.paperList[r].originalFiles)
        # update the prediction if present
        tn = int(self.exM.paperList[r].test)
        if tn in self.predictedTestToNumbers:
            psid = self.predictedTestToNumbers[tn]  # predicted student ID
            psnid = self.student_id_to_snid[psid]  # predicted SNID
            pname = self.snid_to_student_name[psnid]  # predicted student name
            if pname == "":
                self.ui.predictionBox.hide()
            else:
                self.ui.predictionBox.show()
                self.ui.pSIDLabel.setText(psid)
                self.ui.pNameLabel.setText(pname)
        else:
            self.ui.pSIDLabel.setText("")
            self.ui.pNameLabel.setText("")
        # now update the snid entry line-edit.
        # if test is already identified then populate the idlinedit accordingly
        if self.exM.paperList[r].status == "identified":
            snid = "{}: {}".format(
                self.exM.paperList[r].sid, self.exM.paperList[r].sname
            )
            self.ui.idEdit.setText(snid)
        else:  # leave it blank.
            self.ui.idEdit.clear()
        self.ui.idEdit.setFocus()

    def addPaperToList(self, paper, update=True):
        # Add paper to the exam-table-model - get back the corresponding row.
        r = self.exM.addPaper(paper)
        # select that row and display the image
        if update:
            # One more unid'd paper
            self.ui.tableView.selectRow(r)
            self.updateImage(r)

    def updateProgress(self):
        # update progressbars
        try:
            v, m = messenger.IDprogressCount()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
        if m == 0:
            v, m = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.idProgressBar.setFormat("No papers to identify")
            ErrorMessage("No papers to identify.").exec_()
        else:
            self.ui.idProgressBar.resetFormat()
        self.ui.idProgressBar.setMaximum(m)
        self.ui.idProgressBar.setValue(v)

    def requestNext(self):
        """Ask the server for an unID'd paper.   Get file, add to the
        list of papers and update the image.
        """
        self.updateProgress()

        attempts = 0
        while True:
            # TODO - remove this little sanity check else replace with a pop-up warning thingy.
            if attempts >= 5:
                return False
            else:
                attempts += 1
            # ask server for ID of next task
            try:
                test = messenger.IDaskNextTask()
                if not test:  # no tasks left
                    ErrorMessage("No more tasks left on server.").exec_()
                    return False
            except PlomSeriousException as err:
                self.throwSeriousError(err)
                return False

            try:
                imageList = messenger.IDclaimThisTask(test)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
        # Image names = "i<testnumber>.<imagenumber>.<ext>"
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(self.workingDirectory, "i{}.{}.image".format(test, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])

        # Add the paper [code, filename, etc] to the list
        self.addPaperToList(Paper(test, inames))

        # Clean up table - and set focus on the ID-lineedit so user can
        # just start typing in the next ID-number.
        self.ui.tableView.resizeColumnsToContents()
        self.ui.idEdit.setFocus()
        return True

    def acceptPrediction(self):
        # first check currently selected paper is unidentified - else do nothing
        index = self.ui.tableView.selectedIndexes()
        status = self.exM.data(index[1])
        if status != "unidentified":
            msg = SimpleMessage("Do you want to change the ID?")
            # Put message popup on top-corner of idenfier window
            if msg.exec_() == QMessageBox.No:
                return
        code = self.exM.data(index[0])
        sname = self.ui.pNameLabel.text()
        sid = self.ui.pSIDLabel.text()

        if not self.identifyStudent(index, sid, sname):
            return

        if index[0].row() == self.exM.rowCount() - 1:  # at bottom of table.
            self.requestNext()  # updates progressbars.
        else:  # else move to the next unidentified paper.
            self.moveToNextUnID()  # doesn't
            self.updateProgress()
        return

    def identifyStudent(self, index, sid, sname, blank=False, no_id=False):
        """Push identification of a paper to the server and misc UI table.

        User ID's the student of the current paper. Some care around whether
        or not the paper was ID'd previously. Not called directly - instead
        is called by "enterID" or "acceptPrediction" when user hits return on the line-edit.

        Args:
            index: an index into the UI table of the currently
                highlighted row.
            sname (str): The student name or special placeholder.
                - note that this should always be non-trivial string.
            sid (str/None): The student ID or None.
                - note that this is either 'None' (but only if blank or no_id is true), or
                should have passed the 'is_valid_id' test.
            blank (bool): the paper was blank: `sid` must be None and
                `sname` must be `"Blank paper"`.
            no_id (bool): paper is not blank but student did not fill-in
                the ID page(s).  `sid` must be None and `sname` must be
                `"No ID given"`.

        Returns:
            True/False/None: True on success, False/None on failure.
        """
        # do some sanity checks on inputs.
        assert isinstance(sname, str), "Student must be a string"
        assert len(sname) > 0, "Student name cannot be empty"
        # check that sid is none only when blank or no_id is true
        if sid is None:
            assert (
                blank or no_id
            ), "Student ID is only None-type when blank paper or no ID given."
        # similarly blank only when sid=None and sname = "Blank paper"
        if blank:
            assert (sid is None) and (
                sname == "Blank paper"
            ), "Blank should only be true when sid=None and sname = 'Blank paper'"
        # similarly no_id only when sid=None and sname = "No ID given"
        if no_id:
            assert (sid is None) and (
                sname == "No ID given"
            ), "No_id should only be true when sid=None and sname = 'No ID given'"

        # Pass the info to the exam model to put data into the table.
        self.exM.identifyStudent(index, sid, sname)
        code = self.exM.data(index[0])
        # Return paper to server with the code, ID, name.
        try:
            # TODO - do we need this return value
            msg = messenger.IDreturnIDdTask(code, sid, sname)
        except PlomBenignException as err:
            self.throwBenign(err)
            # If an error, revert the student and clear things.
            self.exM.revertStudent(index)
            return False
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return
        # successful ID
        # Issue #25: Use timer to avoid macOS conflict between completer and
        # clearing the line-edit. Very annoying but this fixes it.
        QTimer.singleShot(0, self.ui.idEdit.clear)
        # Update progressbars
        self.updateProgress()
        return True

    def moveToNextUnID(self):
        # Move to the next test in table which is not ID'd.
        rt = self.exM.rowCount()
        if rt == 0:
            return
        rstart = self.ui.tableView.selectedIndexes()[0].row()
        r = (rstart + 1) % rt
        # Be careful to not get stuck in loop if all are ID'd.
        while self.exM.data(self.exM.index(r, 1)) == "identified" and r != rstart:
            r = (r + 1) % rt
        self.ui.tableView.selectRow(r)

    def enterID(self):
        """Triggered when user hits return in the ID-lineedit.. that is
        when they have entered a full student ID.
        """
        # check that the student name / id line-edit has some text.
        if len(self.ui.idEdit.text()) == 0:
            ErrorMessage(
                'Please use the "blank page" button if student has not given their name or ID.'
            ).exec_()
            return

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
        alreadyIDd = False
        # If the paper is already ID'd ask the user if they want to
        # change it - set the alreadyIDd flag to true.
        if status == "identified":
            msg = SimpleMessage("Do you want to change the ID?")
            # Put message popup on top-corner of idenfier window
            if msg.exec_() == QMessageBox.No:
                return
            else:
                alreadyIDd = True

        # Check if the entered SNID (student name and id) is in the list from the classlist.
        if self.ui.idEdit.text() in self.snid_to_student_id:
            # Ask user to confirm ID/Name
            msg = SimpleMessage(
                'Student "{}". Save and move to next?'.format(self.ui.idEdit.text())
            )
            # Put message popup in its last location
            if self.msgGeometry is not None:
                msg.setGeometry(self.msgGeometry)

            # If user says "no" then just return from function.
            if msg.exec_() == QMessageBox.No:
                self.msgGeometry = msg.geometry()
                return
            self.msgGeometry = msg.geometry()

            snid = self.ui.idEdit.text()
            sid = self.snid_to_student_id[snid]
            sname = self.snid_to_student_name[snid]

        else:
            # Number is not in class list - ask user if they really want to
            # enter that number.
            msg = SimpleMessage(
                'Student "{}" not found in classlist. Do you want to input the ID and name manually?'.format(
                    self.ui.idEdit.text()
                )
            )
            # Put message popup on top-corner of idenfier window
            msg.move(self.pos())
            # If no then return from function.
            if msg.exec_() == QMessageBox.No:
                self.msgPosition = msg.pos()
                return
            self.msgPosition = msg.pos()
            # Otherwise get an id and name from the user (and the okay)
            snidbox = SNIDBox(self.ui.idEdit.text())
            if snidbox.exec_() != QDialog.Accepted:
                return
            sid = snidbox.sid.strip()
            sname = snidbox.sname.strip()
            # note sid, sname will not be None-types.
            if not isValidStudentNumber(
                sid
            ):  # this should not happen as snidbox checks.
                return
            if not sname:  # this should not happen as snidbox checks.
                return

            # check if SID is actually in classlist.
            if sid in self.student_id_to_snid:
                ErrorMessage(
                    'ID "{}" is in class list as "{}"'.format(
                        sid, self.student_id_to_snid[sid]
                    )
                ).exec_()
                return
            snid = "{}: {}".format(sid, sname)
            # update our lists
            self.snid_to_student_id[snid] = sid
            self.snid_to_student_name[snid] = sname
            self.student_id_to_snid[sid] = sid
            # finally update the line-edit.  TODO: remove? used to be for identifyStudent call below but not needed anymore?
            self.ui.idEdit.setText(snid)

        # Run identify student command (which talks to server)
        if self.identifyStudent(index, sid, sname):
            if alreadyIDd:
                self.moveToNextUnID()
                return
            if index[0].row() == self.exM.rowCount() - 1:  # last row is highlighted
                if self.requestNext():
                    return
            self.moveToNextUnID()

    def viewWholePaper(self):
        index = self.ui.tableView.selectedIndexes()
        if len(index) == 0:
            return
        testNumber = self.exM.data(index[0])
        try:
            pageNames, imagesAsBytes = messenger.MrequestWholePaper(testNumber)
        except PlomBenignException as err:
            self.throwBenign(err)

        viewFiles = []
        for iab in imagesAsBytes:
            tfn = tempfile.NamedTemporaryFile(delete=False).name
            viewFiles.append(tfn)
            with open(tfn, "wb") as fh:
                fh.write(iab)
        WholeTestView(viewFiles).exec_()

    def blankPaper(self):
        # first check currently selected paper is unidentified - else do nothing
        index = self.ui.tableView.selectedIndexes()
        if len(index) == 0:
            return
        status = self.exM.data(index[1])
        # if status != "unidentified":
        # return
        code = self.exM.data(index[0])
        rv = BlankIDBox(self, code).exec_()
        # return values 0=cancel, 1=blank paper, 2=no id given.
        if rv == 0:
            return
        elif rv == 1:
            # return with sname ='blank paper', and sid = None
            self.identifyStudent(index, None, "Blank paper", blank=True)
        else:
            # return with sname ='no id given', and sid = None
            self.identifyStudent(index, None, "No ID given", no_id=True)

        if index[0].row() == self.exM.rowCount() - 1:  # at bottom of table.
            self.requestNext()  # updates progressbars.
        else:  # else move to the next unidentified paper.
            self.moveToNextUnID()  # doesn't
            self.updateProgress()
        return
