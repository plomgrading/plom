# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2022-2023 Natalie Balashov

"""
The Plom Identifier client
"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import imghdr
import logging
from pathlib import Path
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
from PyQt5.QtWidgets import (
    QCompleter,
    QDialog,
    QWidget,
    QMessageBox,
)

from plom.plom_exceptions import (
    PlomBenignException,
    PlomConflict,
    PlomNoClasslist,
    PlomSeriousException,
    PlomTakenException,
)
from plom import isValidStudentNumber

# from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

from .image_view_widget import ImageViewWidget
from .useful_classes import ErrorMsg, WarnMsg, InfoMsg
from .useful_classes import SimpleQuestion, WarningQuestion
from .useful_classes import BlankIDBox, SNIDBox
from .uiFiles.ui_identify import Ui_IdentifyWindow
from .viewers import WholeTestView


log = logging.getLogger("identr")


class Paper:
    """A simple container for storing a test's idgroup code (tgv) and
    the associated filename for the image. Once identified also
    store the studentName and ID-number.
    """

    def __init__(self, test, fname=None, *, stat="unidentified", id="", name=""):
        # tgv = t0000p00v0
        # ... = 0123456789
        # The test number
        self.test = test
        # Set status as unid'd
        self.status = stat
        # no name or id-number yet.
        self.sname = name
        self.sid = id
        self.originalFile = fname

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
class IDClient(QWidget):
    my_shutdown_signal = pyqtSignal(int)

    def __init__(self, Qapp, tmpdir=None):
        """Initialize the Identifier Client.

        Args:
            Qapp(QApplication): Main client application
            tmpdir (pathlib.Path/str/None): a temporary directory for
                storing image files and other data.  In principle can
                be shared with Marker although this may not be implemented.
                If `None`, we will make our own.
        """
        super().__init__()
        self.Qapp = Qapp
        # instance vars that get initialized later
        # Save the local temp directory for image files and the class list.
        if not tmpdir:
            tmpdir = tempfile.mkdtemp(prefix="plom_")
        self.workingDirectory = Path(tmpdir)
        self.msgr = None

    def setup(self, messenger):
        """Performs setup procedure for the IDClient.

        Args:
            messenger (Messenger): handles communication with server.

        TODO: move all this into init?
        """
        self.msgr = messenger
        # List of papers we have to ID.
        self.paperList = []
        # Fire up the interface.
        self.ui = Ui_IdentifyWindow()
        self.ui.setupUi(self)
        # Paste username into the GUI (TODO: but why?)
        self.ui.userLabel.setText(self.msgr.username)
        # Exam model for the table of papers - associate to table in GUI.
        self.exM = ExamModel()
        self.ui.tableView.setModel(self.exM)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ImageViewWidget(self)
        self.ui.rightPaneLayout.addWidget(self.testImg, 10)

        self.ui.closeButton.clicked.connect(self.close)

        # Get the classlist from server for name/ID completion.
        try:
            self.getClassList()
        except PlomNoClasslist as e:
            WarnMsg(
                self,
                "Cannot identify papers until server has a classlist.",
                info=str(e),
            ).exec()
            return

        # Init the name/ID completers and a validator for ID
        self.setCompleters()
        # Get the predicted list from server for ID guesses.
        self.getPredictions()

        # Connect buttons and key-presses to functions.
        self.ui.idEdit.returnPressed.connect(self.enterID)
        self.ui.nextButton.clicked.connect(self.skipOnClick)
        self.ui.predButton0.clicked.connect(self.acceptPrediction0)
        self.ui.predButton1.clicked.connect(self.acceptPrediction1)
        self.ui.blankButton.clicked.connect(self.blankPaper)
        self.ui.viewButton.clicked.connect(self.viewWholePaper)

        # Make sure no button is clicked by a return-press
        self.ui.nextButton.setAutoDefault(False)
        self.ui.closeButton.setAutoDefault(False)

        # Make sure window is maximised and request a paper from server.
        self.showMaximized()
        # Get list of papers already ID'd and add to table.
        self.getAlreadyIDList()

        # Connect the view **after** list updated.
        # Connect the table's model sel-changed to appropriate function.
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        self.requestNext()

        # TODO: seems to behave ok without this hack: delete?
        # self.testImg.forceRedrawOrSomeBullshit()

        # Create variable to store ID/Name conf window position
        # Initially set to top-left corner of window
        self.msgGeometry = None

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

        Here and throughout 'snid' means "student_id_and_name" as one string.

        Returns nothing but modifies the state of self, adding three
        dicts to the class data:

        `snid_to_student_id`
        `snid_to_student_name`
        `student_id_to_snid`

        Raises:
            PlomNoClasslist
        """
        classlist = self.msgr.IDrequestClasslist()
        self.snid_to_student_id = dict()
        self.snid_to_student_name = dict()
        self.student_id_to_snid = dict()
        name_list = []
        for person in classlist:
            # TODO: Issue #1646 here we want student number with id fallback?
            sid = person["id"]
            sname = person["name"]
            snid = f"{sid}: {sname}"
            self.snid_to_student_id[snid] = sid
            self.snid_to_student_name[snid] = sname
            self.student_id_to_snid[sid] = snid

            if sname in name_list:
                log.warning(
                    'Just FYI: multiple students with name "%s"', censorName(sname)
                )
            name_list.append(sname)

    def getPredictions(self):
        """Send request for prediction list to server.

        For some reason, this also updates font-sizes and stuff.
        """
        self.predictions = self.msgr.IDgetPredictions()

        # Also tweak font size
        fnt = self.font()
        fnt.setPointSize(fnt.pointSize() * 2)
        self.ui.pNameLabel0.setFont(fnt)
        self.ui.pNameLabel1.setFont(fnt)
        # also tweak size of "accept prediction" button font
        self.ui.predButton0.setFont(fnt)
        self.ui.predButton1.setFont(fnt)
        # make the SID larger still.
        fnt.setPointSizeF(fnt.pointSize() * 1.5)
        self.ui.pSIDLabel0.setFont(fnt)
        self.ui.pSIDLabel1.setFont(fnt)
        # And if no predictions then hide that box
        # TODO do this on a paper-by-paper basis
        if not self.predictions:
            self.ui.predictionBox0.hide()
            self.ui.predictionBox1.hide()

    def setCompleters(self):
        """Set up the studentname + studentnumber line-edit completers.
        Means that user can enter the first few numbers (or letters) and
        be prompted with little pop-up with list of possible completions.
        """
        # Build stringlistmodels - one for combined student_name_and_id = snid
        snidlist = QStringListModel()
        # Feed in the numbers and names.
        snidlist.setStringList(list(self.snid_to_student_id.keys()))
        # Build the snid-completer = substring matching and case insensitive
        snidcompleter = QCompleter()
        snidcompleter.setModel(snidlist)
        snidcompleter.setCaseSensitivity(Qt.CaseInsensitive)
        snidcompleter.setFilterMode(Qt.MatchContains)
        # Link the ID-completer to the ID-lineedit in the gui.
        self.ui.idEdit.setCompleter(snidcompleter)
        # Make sure lineedit has little "Clear this" button.
        self.ui.idEdit.setClearButtonEnabled(True)

    def shutDownError(self):
        """Shuts down self due to error."""
        log.error("Shutting down due to error")
        self.close()

    def closeEvent(self, event):
        log.debug("Something has triggered a shutdown event")
        log.debug("Revoking login token")
        self.msgr.closeUser()
        self.my_shutdown_signal.emit(1)
        event.accept()
        log.debug("Identifier: goodbye!")

    def getAlreadyIDList(self):
        # Ask server for list of previously ID'd papers
        idList = self.msgr.IDrequestDoneTasks()
        for x in idList:
            self.addPaperToList(
                Paper(x[0], fname=None, stat="identified", id=x[1], name=x[2]),
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
        if self.exM.paperList[r].originalFile is not None:
            return
        # else try to grab it from server
        try:
            imageDat = self.msgr.request_ID_image(test)
        except PlomBenignException as e:
            log.error("Somewhat unexpected error getting image for %s: %s", test, e)
            WarnMsg(self, f'Unexpected but benign exception:\n"{e}"').exec()
            # self.exM.removePaper(r)
            return

        if imageDat is None:  # means no image
            imageName = None
        else:
            image_ext = imghdr.what(None, h=imageDat)
            if not image_ext:
                msg = f"Failed to identify extension of {len(imageDat)} bytes"
                msg += f" of image data for test {test}"
                log.error(msg)
                WarnMsg(self, msg).exec()
                imageName = None
            else:
                imageName = self.workingDirectory / f"i{test}.0.{image_ext}"
                with open(imageName, "wb") as fh:
                    fh.write(imageDat)

        self.exM.paperList[r].originalFile = imageName

    def updateImage(self, r=0):
        # Here the system should check if imagefile exist and grab if needed.
        self.checkFiles(r)
        # Update the test-image pixmap with the image in the indicated file.
        self.testImg.updateImage(self.exM.paperList[r].originalFile, keep_zoom=True)
        # update the prediction if present
        tn = int(self.exM.paperList[r].test)

        # get a list of predictions for test number tn
        all_predictions_for_paper = self.predictions.get(str(tn), None)

        if all_predictions_for_paper:
            for pred in all_predictions_for_paper:
                psid = pred["student_id"]  # predicted student ID
                psnid = self.student_id_to_snid[psid]  # predicted SNID
                pname = self.snid_to_student_name[psnid]  # predicted student name
                if pname == "":
                    # disable accept prediction button
                    pred = []

                if pred["predictor"] == "prename":
                    self.ui.predButton0.show()
                    self.ui.pSIDLabel0.setText(psid)
                    self.ui.pNameLabel0.setText(pname)
                    self.ui.predictionBox0.setTitle(
                        "Prenamed paper: is it signed?  if not signed, is it blank?"
                    )
                    self.ui.predButton0.setText("Confirm\n&Prename")
                    self.ui.predictionBox0.setStyleSheet("background-color: #89CFF0")

                    self.ui.predictionBox1.hide()

                elif pred["predictor"] == "MLLAP":
                    self.ui.predButton0.show()
                    self.ui.pSIDLabel0.setText(psid)
                    self.ui.pNameLabel0.setText(pname)
                    self.ui.predictionBox0.setTitle(
                        f"Prediction by MLLAP with certainty {round(pred['certainty'], 3)}"
                    )
                    self.ui.predButton0.setText("&Accept\nPrediction")

                    self.ui.predictionBox1.hide()

                elif pred["predictor"] == "MLGreedy":
                    first_pred = all_predictions_for_paper[0]
                    second_pred = all_predictions_for_paper[1]
                    if first_pred["student_id"] == second_pred["student_id"]:
                        # only single option shown, so keep alt-a shortcut
                        self.ui.predButton0.setText("&Accept\nPrediction")
                        self.ui.predictionBox0.setTitle(
                            f"{first_pred['predictor']} prediction with certainty {round(first_pred['certainty'], 3)} agrees with {second_pred['predictor']} prediction of certainty {round(second_pred['certainty'], 3)}"
                        )
                    else:
                        self.ui.predictionBox1.show()
                        self.ui.predButton1.show()
                        self.ui.pSIDLabel1.setText(psid)
                        self.ui.pNameLabel1.setText(pname)
                        self.ui.predictionBox1.setTitle(
                            f"Prediction by MLGreedy with certainty {round(pred['certainty'], 3)}"
                        )
                        # two predictions shown - not alt-a shortcut.
                        self.ui.predButton0.setText("Accept\nPrediction")
                        self.ui.predButton1.setText("Accept\nPrediction")

                    if first_pred["student_id"] != second_pred["student_id"]:
                        self.ui.predictionBox0.setStyleSheet(
                            "background-color: #FFD700"
                        )
                        self.ui.predictionBox1.setStyleSheet(
                            "background-color: #FFD700"
                        )
                    elif (
                        pred["certainty"] < 0.3
                    ):  # inaccurate Greedy prediction tend to have certainty less than 0.3
                        # useful to warn the user if LAP agrees with Greedy, but both have a high chance of being incorrect
                        self.ui.predictionBox0.setStyleSheet(
                            "background-color: #FF7F50"
                        )
                    else:
                        self.ui.predictionBox0.setStyleSheet(
                            "background-color: #00FA9A"
                        )
                else:
                    raise RuntimeError(
                        f"Found unexpected predictions by predictor {pred['predictor']}, which should not be here."
                    )

        else:
            self.ui.predButton0.hide()
            self.ui.pSIDLabel0.setText("")
            self.ui.pNameLabel0.setText("")
            self.ui.predictionBox0.setTitle("No prediction")
            self.ui.predictionBox0.setStyleSheet("background-color:")
            self.ui.predictionBox1.hide()

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
        v, m = self.msgr.IDprogressCount()
        if m == 0:
            v, m = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.idProgressBar.setFormat("No papers to identify")
            InfoMsg(self, "No papers to identify.").exec()
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
                test = self.msgr.IDaskNextTask()
                if not test:  # no tasks left
                    InfoMsg(self, "No more tasks left on server.").exec()
                    return False
            except PlomSeriousException as err:
                log.exception("Unexpected error getting next task: %s", err)
                ErrorMsg(
                    self,
                    f"Unexpected error getting next task:\n{err}\nClient will now crash!",
                ).exec()
                raise

            try:
                self.msgr.IDclaimThisTask(test)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue

        img_bytes = self.msgr.request_ID_image(test)
        img_ext = imghdr.what(None, h=img_bytes)
        if not img_ext:
            msg = f"Failed to identify extension of {len(img_bytes)} bytes"
            msg += f" of image data for test {test}"
            log.error(msg)
            raise PlomSeriousException(msg)
        filename = self.workingDirectory / f"i{test}.0.{img_ext}"
        with open(filename, "wb") as fh:
            fh.write(img_bytes)

        # Add the paper [code, filename, etc] to the list
        self.addPaperToList(Paper(test, filename))

        # Clean up table - and set focus on the ID-lineedit so user can
        # just start typing in the next ID-number.
        self.ui.tableView.resizeColumnsToContents()
        self.ui.idEdit.setFocus()
        return True

    def acceptPrediction0(self):
        return self._acceptPrediction(which_one=0)

    def acceptPrediction1(self):
        return self._acceptPrediction(which_one=1)

    def _acceptPrediction(self, which_one):
        # first check currently selected paper is unidentified - else do nothing
        index = self.ui.tableView.selectedIndexes()
        status = self.exM.data(index[1])
        if status != "unidentified":
            msg = SimpleQuestion(self, "Do you want to change the ID?")
            # Put message popup on top-corner of idenfier window
            if msg.exec() == QMessageBox.No:
                return
        # code = self.exM.data(index[0])

        if which_one == 0:
            sname = self.ui.pNameLabel0.text()
            sid = self.ui.pSIDLabel0.text()
        elif which_one == 1:
            sname = self.ui.pNameLabel1.text()
            sid = self.ui.pSIDLabel1.text()
        else:
            return

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
            self.msgr.IDreturnIDdTask(code, sid, sname)
        except PlomConflict as err:
            log.warn("Conflict when returning paper %s: %s", code, err)
            hints = """
                <p>If you are unable to resolve this conflict, you may need
                to use the Manager tool to "Un-ID" the other paper.</p>
            """
            WarnMsg(self, str(err), info=hints, info_pre=False).exec()
            self.exM.revertStudent(index)
            return False
        except PlomBenignException as err:
            log.error("Somewhat unexpected error when returning %s: %s", code, err)
            WarnMsg(self, f'Unexpected but benign exception:\n"{err}"').exec()
            self.exM.revertStudent(index)
            return False
        # successful ID
        # Issue #23: Use timer to avoid macOS conflict between completer and
        # clearing the line-edit. Very annoying but this fixes it.
        QTimer.singleShot(0, self.ui.idEdit.clear)
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
            InfoMsg(
                self,
                'Please use the "Blank page" button if student has not '
                "given their name or ID.",
            ).exec()
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
            msg = SimpleQuestion(self, "Do you want to change the ID?")
            # Put message popup on top-corner of idenfier window
            if msg.exec() == QMessageBox.No:
                return
            else:
                alreadyIDd = True

        # Check if the entered SNID (student name and id) is in the list from the classlist.
        if self.ui.idEdit.text() in self.snid_to_student_id:
            # Ask user to confirm ID/Name
            msg = SimpleQuestion(
                self,
                f'Student "<b>{self.ui.idEdit.text()}</b>".',
                "Save and move to next?",
            )
            # Put message popup in its last location
            if self.msgGeometry is not None:
                msg.setGeometry(self.msgGeometry)

            # If user says "no" then just return from function.
            if msg.exec() == QMessageBox.No:
                self.msgGeometry = msg.geometry()
                return
            self.msgGeometry = msg.geometry()

            snid = self.ui.idEdit.text()
            sid = self.snid_to_student_id[snid]
            sname = self.snid_to_student_name[snid]

        else:
            msg = WarningQuestion(
                self,
                f'Student "{self.ui.idEdit.text()}" not found in classlist.',
                "Do you want to input the ID and name manually?",
            )
            # Put message popup on top-corner of idenfier window
            msg.move(self.pos())
            # If no then return from function.
            if msg.exec() == QMessageBox.No:
                self.msgPosition = msg.pos()
                return
            self.msgPosition = msg.pos()
            # Otherwise get an id and name from the user (and the okay)
            snidbox = SNIDBox(self, self.ui.idEdit.text())
            if snidbox.exec() != QDialog.Accepted:
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
                WarnMsg(
                    self,
                    f"<p>ID &ldquo;{sid}&rdquo; is in classlist as "
                    f"&ldquo;{self.student_id_to_snid[sid]}&rdquo;.</p>"
                    "<p>Cannot enter them into the classlist without "
                    "a unique ID.</p>",
                ).exec()
                return
            snid = f"{sid}: {sname}"
            # update our lists
            self.snid_to_student_id[snid] = sid
            self.snid_to_student_name[snid] = sname
            self.student_id_to_snid[sid] = snid
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
        testnum = self.exM.data(index[0])
        pagedata = self.msgr.get_pagedata(testnum)
        pagedata = self.Qapp.downloader.sync_downloads(pagedata)
        labels = [x["pagename"] for x in pagedata]
        WholeTestView(testnum, pagedata, labels, parent=self).exec()

    def blankPaper(self):
        # first check currently selected paper is unidentified - else do nothing
        index = self.ui.tableView.selectedIndexes()
        if len(index) == 0:
            return
        # status = self.exM.data(index[1])
        # if status != "unidentified":
        # return
        code = self.exM.data(index[0])
        rv = BlankIDBox(self, code).exec()
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
