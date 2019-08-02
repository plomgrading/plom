__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import os
import json
import shutil
import tempfile
import time

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QElapsedTimer,
    QModelIndex,
    QObject,
    QSettings,
    QSortFilterProxyModel,
    QTimer,
    QThread,
    pyqtSignal,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QDialog, QMessageBox, QPushButton


from examviewwindow import ExamViewWindow
import messenger
from annotator import Annotator
from useful_classes import AddTagBox, ErrorMessage, SimpleMessage
from reorientationwindow import ExamReorientWindow
from uiFiles.ui_marker import Ui_MarkerWindow

# in order to get shortcuts under OSX this needs to set this.... but only osx.
# To test platform
import platform

if platform.system() == "Darwin":
    from PyQt5.QtGui import qt_set_sequence_auto_mnemonic

    qt_set_sequence_auto_mnemonic(True)

# set up variables to store paths for marker and id clients
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

# Read https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
# and https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
# and finally https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
# I'll do it the simpler subclassing way
class BackgroundDownloader(QThread):
    downloaded = pyqtSignal(str)

    def setFiles(self, tname, fname):
        self.tname = tname
        self.fname = fname

    def run(self):
        messenger.getFileDav(self.tname, self.fname)
        # needed to send "please delete" back to server
        self.downloaded.emit(self.tname)
        # then exit
        self.quit()


class BackgroundUploader(QThread):
    uploaded = pyqtSignal(str, str, str, str, str, int, str)

    def setUploadInfo(self, code, gr, aname, pname, cname, mtime, tags):
        self.code = code
        self.gr = gr
        self.aname = aname
        self.pname = pname
        self.cname = cname
        self.mtime = mtime
        self.tags = tags

    def run(self):
        afile = os.path.basename(self.aname)
        messenger.putFileDav(self.aname, afile)
        # copy plom file to webdav
        pfile = os.path.basename(self.pname)
        messenger.putFileDav(self.pname, pfile)
        # copy comment file to webdav
        cfile = os.path.basename(self.cname)
        messenger.putFileDav(self.cname, cfile)

        # needed to send "please delete" back to server
        self.uploaded.emit(
            self.code, self.gr, afile, pfile, cfile, self.mtime, self.tags
        )
        # then exit
        self.quit()


class TestPageGroup:
    """A simple container for storing a groupimage's code (tgv),
    numer, group, version, status, the mark, the original image
    filename, the annotated image filename, the mark, and the
    time spent marking the groupimage.
    """

    def __init__(self, tgv, fname="", stat="untouched", mrk="-1", mtime="0", tags=""):
        # tgv = t0000p00v0
        # ... = 0123456789
        # the test code
        self.prefix = tgv
        # the test number
        self.status = stat
        # By default set mark to be negative (since 0 is a possible mark)
        self.mark = mrk
        # The filename of the untouched image
        self.originalFile = fname
        # The filename for the (future) annotated image
        self.annotatedFile = ""
        # The filename for the (future) plom file
        self.plomFile = ""
        # The time spent marking the image.
        self.markingTime = mtime
        # Any user tags/comments
        self.tags = tags


class ExamModel(QStandardItemModel):
    """A tablemodel for handling the group image marking data."""

    def __init__(self, parent=None):
        QStandardItemModel.__init__(self, parent)
        self.setHorizontalHeaderLabels(
            [
                "TGV",
                "Status",
                "Mark",
                "Time",
                "Tag",
                "OriginalFile",
                "AnnotatedFile",
                "PlomFile",
            ]
        )

    def markPaper(self, index, mrk, aname, mtime, pname):
        # When marked, set the annotated filename, the mark,
        # and the total marking time (in case it was annotated earlier)
        mt = self.itemData(index[3])
        # total elapsed time.
        self.setData(index[3], mtime + mt)
        self.setData(index[1], "marked")
        self.setData(index[2], mrk)
        self.setData(index[6], aname)
        self.setData(index[7], pname)

    def addPaper(self, paper):
        # Append new groupimage to list and append new row to table.
        r = self.rowCount()
        self.appendRow(
            [
                QStandardItem(paper.prefix),
                QStandardItem(paper.status),
                QStandardItem(str(paper.mark)),
                QStandardItem(str(paper.markingTime)),
                QStandardItem(paper.tags),
                QStandardItem(paper.originalFile),
                QStandardItem(paper.annotatedFile),
                QStandardItem(paper.plomFile),
            ]
        )
        return r


##########################
class ProxyModel(QSortFilterProxyModel):
    """A proxymodel wrapper to put around the table model to handle filtering and sorting."""

    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.setFilterKeyColumn(4)
        self.filterString = ""

    def setFilterString(self, flt):
        self.filterString = flt

    def filterTags(self):
        self.setFilterFixedString(self.filterString)

    def filterAcceptsRow(self, pos, index):
        if len(self.filterString) == 0:
            return True
        if (
            self.filterString.casefold()
            in self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
        ):
            return True
        return False

    def addPaper(self, rho):
        # Append new groupimage to list and append new row to table.
        r = self.sourceModel().addPaper(rho)
        pr = self.mapFromSource(self.sourceModel().index(r, 0)).row()
        return pr

    def getPrefix(self, r):
        # Return the prefix of the image
        return self.data(self.index(r, 0))

    def getStatus(self, r):
        # Return the status of the image
        return self.data(self.index(r, 1))

    def setStatus(self, r, stat):
        # Return the status of the image
        return self.setData(self.index(r, 1), stat)

    def getOriginalFile(self, r):
        # Return the filename of the original un-annotated image
        return self.data(self.index(r, 5))

    def setOriginalFile(self, r, fname):
        # Set the original image filename
        self.setData(self.index(r, 5), fname)

    def getAnnotatedFile(self, r):
        # Return the filename of the annotated image
        return self.data(self.index(r, 6))

    def setAnnotatedFile(self, r, aname, pname):
        # Set the annotated image filename
        self.setData(self.index(r, 6), aname)
        self.setData(self.index(r, 7), pname)

    def getPlomFile(self, r):
        # Return the filename of the plom file
        return self.data(self.index(r, 7))

    def markPaper(self, index, mrk, aname, pname, mtime):
        # When marked, set the annotated filename, the plomfile, the mark,
        # and the total marking time (in case it was annotated earlier)
        mt = int(self.data(index[3]))
        # total elapsed time.
        self.setData(index[3], mtime + mt)
        self.setData(index[1], "marked")
        self.setData(index[2], mrk)
        self.setData(index[0].siblingAtColumn(6), aname)
        self.setData(index[0].siblingAtColumn(7), pname)

    def revertPaper(self, index):
        # When user reverts to original image, set status to "reverted"
        # mark back to -1, and marking time to zero.
        # remove the annotated image file.
        self.setData(index[1], "reverted")
        self.setData(index[2], -1)
        self.setData(index[3], 0)
        # remove annotated picture and plom file
        os.remove("{}".format(self.data(index[0].siblingAtColumn(6))))
        os.remove("{}".format(self.data(index[0].siblingAtColumn(7))))

    def deferPaper(self, index):
        # When user defers paper, it must be unmarked or reverted already. Set status to "deferred"
        self.setData(index[1], "deferred")


##########################


class MarkerClient(QDialog):
    def __init__(
        self,
        userName,
        password,
        server,
        message_port,
        web_port,
        pageGroup,
        version,
        parent=None,
    ):
        # Init the client with username, password, server and port data,
        # and which group/version is being marked.
        super(MarkerClient, self).__init__(parent)
        # Fire up the messenger with server data.
        messenger.setServerDetails(server, message_port, web_port)
        messenger.startMessenger()
        # Ping to see if server is up.
        if not messenger.pingTest():
            QTimer.singleShot(100, self.reject)
            self.testImg = None  # so that resize event doesn't throw error
            return
        # Save username, password, and path the local temp directory for
        # image files and the class list.
        self.userName = userName
        self.password = password
        self.workingDirectory = directoryPath
        # Save the group and version.
        self.pageGroup = pageGroup
        self.version = version
        # create max-mark, but not set until we get info from server
        self.maxScore = -1
        # Fire up the user interface
        self.ui = Ui_MarkerWindow()
        self.ui.setupUi(self)
        # Paste the username, pagegroup and version into GUI.
        self.ui.userLabel.setText(self.userName)
        self.ui.pgLabel.setText(str(self.pageGroup).zfill(2))
        self.ui.vLabel.setText(str(self.version))
        # Exam model for the table of groupimages - connect to table
        self.exM = ExamModel()
        # set proxy for filtering and sorting
        self.prxM = ProxyModel()
        self.prxM.setSourceModel(self.exM)
        self.ui.tableView.setModel(self.prxM)
        self.ui.tableView.hideColumn(5)  # hide original filename
        self.ui.tableView.hideColumn(6)  # hide annotated filename
        self.ui.tableView.hideColumn(7)  # hide plom filename
        # Double-click or signale fires up the annotator window
        self.ui.tableView.doubleClicked.connect(self.annotateTest)
        self.ui.tableView.annotateSignal.connect(self.annotateTest)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ExamViewWindow()
        self.ui.gridLayout_6.addWidget(self.testImg, 0, 0)
        # create a settings variable for saving annotator window settings
        self.annotatorSettings = QSettings()
        self.annotatorSettings.clear()  # do not remember between sessions.

        # Connect gui buttons to appropriate functions
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.revertButton.clicked.connect(self.revertTest)
        self.ui.deferButton.clicked.connect(self.deferTest)
        self.ui.tagButton.clicked.connect(self.tagTest)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        # self.ui.filterLE.focusInEvent.connect(lambda: self.ui.filterButton.setFocus())
        # Give IDs to the radio-buttons which select the marking style
        # 1 = mark total = user clicks the total-mark
        # 2 = mark-up = mark starts at 0 and user increments it
        # 3 = mark-down = mark starts at max and user decrements it
        self.ui.markStyleGroup.setId(self.ui.markTotalRB, 1)
        self.ui.markStyleGroup.setId(self.ui.markUpRB, 2)
        self.ui.markStyleGroup.setId(self.ui.markDownRB, 3)
        # Give IDs to the radio buttons which select which mouse-hand is used
        # 0 = Right-handed user will typically have right-hand on mouse and
        # left hand on the keyboard. The annotator layout will follow this.
        # 1 = Left-handed user - reverse layout
        self.ui.mouseHandGroup.setId(self.ui.rightMouseRB, 0)
        self.ui.mouseHandGroup.setId(self.ui.leftMouseRB, 1)
        # Start using connection to serverself.
        # Ask server to authenticate user and return the authentication token
        self.requestToken()
        # Get the max-mark for the question from the server.
        self.getRubric()
        # Paste the max-mark into the gui.
        self.ui.scoreLabel.setText(str(self.maxScore))
        # Get list of papers already marked and add to table.
        self.getMarkedList()
        # Update counts
        self.updateCount()
        # Connect the view **after** list updated.
        # Connect the table-model's selection change to appropriate function
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        # Get a pagegroup to mark from the server
        self.requestNext()
        # reset the view so whole exam shown.
        self.testImg.resetB.animateClick()
        # resize the table too.
        QTimer.singleShot(100, self.ui.tableView.resizeRowsToContents)
        # A thread for downloading in the background
        # see https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
        # and https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
        self.backgroundDownloader = BackgroundDownloader()
        self.backgroundDownloader.downloaded.connect(self.requestNextInBackgroundFinish)
        self.backgroundUploader = BackgroundUploader()
        self.backgroundUploader.uploaded.connect(self.uploadInBackgroundFinish)

    def resizeEvent(self, e):
        if self.testImg is None:
            # pingtest must have failed, so do nothing.
            return
        # On resize used to resize the image to keep it all in view
        self.testImg.resetB.animateClick()
        # resize the table too.
        self.ui.tableView.resizeRowsToContents()
        super(MarkerClient, self).resizeEvent(e)

    def requestToken(self):
        """Send authorisation request (AUTH) to server.

        The request sends name and password (over ssl) to the server. If hash
        of password matches the one of file, then the server sends back an
        "ACK" and an authentication token. The token is then used to
        authenticate future transactions with the server (since password
        hashing is slow).
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

    def getRubric(self):
        """Send request for the max mark (mGMX) to server.
        The server then sends back [ACK, maxmark].
        """
        # Send max-mark request (mGMX) to server
        msg = messenger.SRMsg(
            ["mGMX", self.userName, self.token, self.pageGroup, self.version]
        )
        # Return should be [ACK, maxmark]
        if msg[0] == "ERR":
            quit()
        self.maxScore = msg[1]

    def getMarkedList(self):
        # Ask server for list of previously marked papers
        msg = messenger.SRMsg(
            ["mGML", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        fname = os.path.join(self.workingDirectory, "markedList.txt")
        messenger.getFileDav(msg[1], fname)
        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, msg[1]])
        # Add those marked papers to our paper-list
        with open(fname) as json_file:
            markedList = json.load(json_file)
            for x in markedList:
                self.addTGVToList(
                    TestPageGroup(
                        x[0], fname="", stat="marked", mrk=x[2], mtime=x[3], tags=x[4]
                    ),
                    update=False,
                )

    def addTGVToList(self, paper, update=True):
        # Add a new entry (given inside paper) to the table and
        # select it and update the displayed page-group image
        # convert new row to proxyRow
        pr = self.prxM.addPaper(paper)
        if update is True:
            self.ui.tableView.selectRow(pr)
            self.updateImage(pr)

    def checkFiles(self, pr):
        tgv = self.prxM.getPrefix(pr)
        if self.prxM.getOriginalFile(pr) != "":
            return
        msg = messenger.SRMsg(["mGGI", self.userName, self.token, tgv])
        if msg[0] == "ERR":
            return
        fname = os.path.join(self.workingDirectory, "{}.png".format(msg[1]))
        aname = os.path.join(self.workingDirectory, "G{}.png".format(msg[1][1:]))
        pname = os.path.join(self.workingDirectory, "G{}.plom".format(msg[1][1:]))

        tfname = msg[2]  # the temp original image file on webdav
        taname = msg[3]  # the temp annotated image file on webdav
        tpname = msg[4]  # the temp plom file on webdav
        messenger.getFileDav(tfname, fname)
        # got original file so ask server to remove it.
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, tfname])
        self.prxM.setOriginalFile(pr, fname)
        # If there is an annotated image then get it.
        if taname is None:
            return
        messenger.getFileDav(taname, aname)
        messenger.getFileDav(tpname, pname)
        # got annotated image / plom file so ask server to remove it.
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, taname])
        self.prxM.setAnnotatedFile(pr, aname, pname)

    def updateImage(self, pr=0):
        # Here the system should check if imagefiles exist and grab if needed.
        self.checkFiles(pr)

        # Grab the group-image from file and display in the examviewwindow
        # If group has been marked or annotated then display the annotated file
        # Else display the original group image
        if self.prxM.getStatus(pr) in ["marked", "annotated"]:
            self.testImg.updateImage(self.prxM.getAnnotatedFile(pr))
        else:
            self.testImg.updateImage(self.prxM.getOriginalFile(pr))
        # wait a moment and click the reset-view button
        QTimer.singleShot(100, self.testImg.view.resetView)
        # Give focus to the table (so enter-key fires up annotator)
        self.ui.tableView.setFocus()

    def updateCount(self):
        # ask server for marking-count update
        progress_msg = messenger.SRMsg(
            ["mPRC", self.userName, self.token, self.pageGroup, self.version]
        )
        # returns [ACK, #marked, #total]
        if progress_msg[0] == "ACK":
            self.ui.mProgressBar.setValue(progress_msg[1])
            self.ui.mProgressBar.setMaximum(progress_msg[2])

    def requestNext(self, launchAgain=False):
        """Ask the server for an unmarked paper (mNUM). Server should return
        message [ACK, test-code, temp-filename]. Get file from webdav, add to
        the list of papers and update the image.
        """
        # Ask server for next unmarked paper
        msg = messenger.SRMsg(
            ["mNUM", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        # Return message should be [ACK, code, temp-filename, tags]
        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, msg[1] + ".png")
        # Get file from the tempfilename in the webdav
        tname = msg[2]
        messenger.getFileDav(tname, fname)
        # Add the page-group to the list of things to mark
        self.addTGVToList(TestPageGroup(msg[1], fname, tags=msg[3]))
        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, tname])
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()
        # launch annotator on the new test
        # Note-launch-again is set to true when user just wants to get
        # the next test and get annotating directly.
        # When false the user stays at the marker window
        if msg[0] != "ERR" and launchAgain:
            # do not recurse, instead animate click
            # self.annotateTest()
            self.ui.annButton.animateClick()

    def requestNextInBackgroundStart(self):
        # Ask server for next unmarked paper
        msg = messenger.SRMsg(
            ["mNUM", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        # Return message should be [ACK, code, temp-filename, tags]
        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, msg[1] + ".png")
        # Get file from the tempfilename in the webdav
        tname = msg[2]
        # Do this `messenger.getFileDav(tname, fname)` in another thread
        self.backgroundDownloader.setFiles(tname, fname)
        self.backgroundDownloader.start()
        # Add the page-group to the list of things to mark
        self.addTGVToList(TestPageGroup(msg[1], fname, tags=msg[3]), update=True)

    def requestNextInBackgroundFinish(self, tname):
        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, tname])
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()

    def moveToNextUnmarkedTest(self):
        # Move to the next unmarked test in the table.
        # Be careful not to get stuck in a loop if all marked
        prt = self.prxM.rowCount()
        if prt == 0:
            return
        # back up one row because before this is called we have
        # added a row in the background, so the current row is actually
        # one too far forward.
        prstart = (self.ui.tableView.selectedIndexes()[0].row() - 1) % prt
        pr = (prstart + 1) % prt
        while self.prxM.getStatus(pr) in ["marked", "deferred"] and pr != prstart:
            pr = (pr + 1) % prt
        self.ui.tableView.selectRow(pr)
        if pr == prstart:
            # gone right round, so select prstart+1
            self.ui.tableView.selectRow((pr + 1) % prt)
            return False
        return True

    def revertTest(self):
        # Get rid of any annotations or marks and go back to unmarked original
        prIndex = self.ui.tableView.selectedIndexes()
        # if no test then return
        if len(prIndex) == 0:
            return
        # If test is untouched or already reverted, nothing to do
        if self.prxM.data(prIndex[1]) in ["untouched", "reverted"]:
            return
        # Check user really wants to revert
        msg = SimpleMessage("Do you want to revert to original scan?")
        if msg.exec_() == QMessageBox.No:
            return
        # Revert the test in the table (set status, mark etc)
        self.prxM.revertPaper(prIndex)
        # Update the image (is now back to original untouched image)
        self.updateImage(prIndex[0].row())

    def deferTest(self):
        # Mark test as "defer" - to be skipped until later.
        index = self.ui.tableView.selectedIndexes()
        # if no test then return
        if len(index) == 0:
            return
        if self.prxM.data(index[1]) == "deferred":
            return
        if self.prxM.data(index[1]) == "marked":
            msg = ErrorMessage("Paper is already marked - revert it before deferring.")
            msg.exec_()
            return
        self.prxM.deferPaper(index)

    def countUnmarkedReverted(self):
        count = 0
        for pr in range(self.prxM.rowCount()):
            if self.prxM.getStatus(pr) in ["untouched", "reverted"]:
                count += 1
        return count

    def waitForAnnotator(self, fname, pname=None):
        """This fires up the annotation window for user annotation + maring.
        Set a timer to record the time spend marking (for manager to see what
        questions are taking a long time or are quick).
        """
        # Set marking style total/up/down - will pass to annotator
        self.markStyle = self.ui.markStyleGroup.checkedId()
        # Set mousehand left/right - will pass to annotator
        self.mouseHand = self.ui.mouseHandGroup.checkedId()
        # Set plom-dictionary to none
        pdict = None
        # check if given a plom-file and set markstyle + pdict accordingly
        if pname is not None:
            with open(pname, "r") as fh:
                pdict = json.load(fh)
            self.markStyle = pdict["markStyle"]
            # there should be a filename sanity check here to
            # make sure plom file matches current image-file

        # Start a timer to record time spend annotating
        timer = QElapsedTimer()
        timer.start()
        # build the annotator - pass it the image filename, the max-mark
        # the markingstyle (up/down/total) and mouse-hand (left/right)
        annotator = Annotator(
            fname,
            self.maxScore,
            self.markStyle,
            self.mouseHand,
            parent=self,
            plomDict=pdict,
        )
        # while annotator is firing up request next paper in background
        # after giving system a moment to do `annotator.exec_()`
        # but check if unmarked papers already in list.
        if self.countUnmarkedReverted() == 0:
            self.requestNextInBackgroundStart()
        # run the annotator
        if annotator.exec_():
            # If annotator returns "accept"
            # then pass back the mark, time spent marking
            # (timer measures millisec, so divide by 1000)
            # and a flag as to whether or not we should relaunch the annotator
            # with the next page-image. In relaunch, then we will need to
            # ask server for next image.
            ret = [str(annotator.score), timer.elapsed() // 1000, annotator.launchAgain]
        else:
            # If annotator returns "reject", then pop up error
            msg = ErrorMessage("mark not recorded")
            msg.exec_()
            ret = [None, timer.elapsed(), False]
        return ret

    def annotateTest(self):
        """Command grabs current test from table and (after checks) passes it
        to 'waitForAnnotator' which fires up the actual annotator.
        Checks if current test has been marked already
        Saves the annotated file, mark, marking time etc in the table.
        Sends file and data back to server.
        """
        # If nothing in the table, return.
        if self.prxM.rowCount() == 0:
            return
        # Grab the currently selected row.
        index = self.ui.tableView.selectedIndexes()
        # Create annotated filename. If original tXXXXgYYvZ.png, then
        # annotated version is GXXXXgYYvZ (G=graded).
        aname = os.path.join(
            self.workingDirectory, "G" + self.prxM.data(index[0])[1:] + ".png"
        )
        cname = aname[:-3] + "json"
        pname = aname[:-3] + "plom"
        # If image has been marked confirm with user if they want
        # to annotate further.
        remarkFlag = False
        if self.prxM.data(index[1]) in ["marked"]:
            msg = SimpleMessage("Continue marking paper?")
            if msg.exec_() == QMessageBox.Yes:
                # Copy the current annotated filename to backup file in case
                # user cancels their annotations.
                shutil.copyfile(aname, aname + ".bak")
                remarkFlag = True
            else:
                return
        # Copy the original image to the annotated filename.
        shutil.copyfile("{}".format(self.prxM.getOriginalFile(index[0].row())), aname)

        # Get mark, markingtime, and launch-again flag from 'waitForAnnotator'
        prevState = self.prxM.data(index[1])
        self.prxM.setData(index[1], "annotating")
        if remarkFlag:
            [gr, mtime, launchAgain] = self.waitForAnnotator(aname, pname)
        else:
            [gr, mtime, launchAgain] = self.waitForAnnotator(aname, None)
        # Exited annotator with 'cancel', so don't save anything.
        if gr is None:
            # if remarking then move backup annotated file back.
            if remarkFlag:
                shutil.move(aname + ".bak", aname)
            # reselect the row we were working on
            self.prxM.setData(index[1], prevState)
            self.ui.tableView.selectRow(index[1].row())
            return
        # Copy the mark, annotated filename and the markingtime into the table
        self.prxM.markPaper(index, gr, aname, pname, mtime)
        # Update the currently displayed image
        self.updateImage(index[1].row())

        # these need to happen in another thread - but that requires
        # us to check with server to make sure user is still authorised
        # to upload this particular pageimage - this may have changed
        # depending on what else is going on.

        msg = messenger.SRMsg(
            ["mUSO", self.userName, self.token, self.prxM.data(index[0])]
        )
        if msg[0] == "ACK":
            # upload in background
            self.uploadInBackgroundStart(
                self.prxM.data(index[0]),  # current tgv
                gr,  # grade
                aname,  # annotated file
                pname,  # plom file
                cname,  # comment file
                mtime,  # marking time
                self.prxM.data(index[4]),  # tags
            )

        # Check if no unmarked test, then request one.
        if launchAgain is False:
            return
        if self.moveToNextUnmarkedTest():
            # self.annotateTest()
            self.ui.annButton.animateClick()

    def uploadInBackgroundStart(self, code, gr, aname, pname, cname, mtime, tags):
        self.backgroundUploader.setUploadInfo(
            code, gr, aname, pname, cname, mtime, tags
        )
        self.backgroundUploader.start()

    def uploadInBackgroundFinish(self, code, gr, afile, pfile, cfile, mtime, tags):
        # Server will save data and copy the annotated file, then delete it
        # from the webdav
        msg = messenger.SRMsg(
            [
                "mRMD",
                self.userName,
                self.token,
                code,
                gr,
                afile,
                pfile,
                cfile,
                mtime,
                self.pageGroup,
                self.version,
                tags,
            ]
        )
        if msg[0] == "ACK":
            # returns [ACK, #done, #total]
            self.ui.mProgressBar.setValue(msg[1])
            self.ui.mProgressBar.setMaximum(msg[2])

    def selChanged(self, selnew, selold):
        # When selection changed, update the displayed image
        idx = selnew.indexes()
        if len(idx) > 0:
            self.updateImage(idx[0].row())

    def shutDown(self):
        # When shutting down, first alert server of any images that were
        # not marked - using 'DNF' (did not finish). Sever will put
        # those files back on the todo pile.
        self.DNF()
        # Then send a 'user closing' message - server will revoke
        # authentication token.
        msg = messenger.SRMsg(["UCL", self.userName, self.token])
        # then close
        self.close()

    def DNF(self):
        # Go through table and send a 'did not finish' message for anything
        # that is not marked.
        # Note - do this for everything, not just the proxy-model
        for r in range(self.exM.rowCount()):
            if self.exM.data(self.exM.index(r, 1)) != "marked":
                # Tell server the code fo any paper that is not marked.
                # server will put that back on the todo-pile.
                msg = messenger.SRMsg(
                    [
                        "mDNF",
                        self.userName,
                        self.token,
                        self.exM.data(self.exM.index(r, 0)),
                    ]
                )

    def viewWholePaper(self):
        index = self.ui.tableView.selectedIndexes()
        tgv = self.prxM.getPrefix(index[0].row())
        testnumber = tgv[1:5]  # since tgv = tXXXXgYYvZ
        msg = messenger.SRMsg(["mGWP", self.userName, self.token, testnumber])
        if msg[0] == "ERR":
            return []

        self.viewFiles = msg[1:]
        self.localViewFiles = []
        ## GIVE FILES NAMES
        for f in self.viewFiles:
            tfn = tempfile.NamedTemporaryFile(delete=False).name
            self.localViewFiles.append(tfn)
            messenger.getFileDav(f, tfn)
        return self.localViewFiles

    def doneWithViewFiles(self):
        for f in self.viewFiles:
            msg = messenger.SRMsg(["mDWF", self.userName, self.token, f])
        for f in self.localViewFiles:
            os.unlink(f)
        self.viewFiles = []

    def latexAFragment(self, txt):
        # create a tempfile
        fname = os.path.join(self.workingDirectory, "fragment")
        dname = (
            self.userName
        )  # call fragment file just the username to avoid collisions
        # write the latex text to that file
        with open(fname, "w") as fh:
            fh.write(txt)
        messenger.putFileDav(fname, dname)

        msg = messenger.SRMsg(["mLTT", self.userName, self.token, dname])
        if msg[1] == True:
            messenger.getFileDav(msg[2], "frag.png")
            messenger.SRMsg(["mDWF", self.userName, self.token, msg[2]])
            return True
        else:
            return False

    def tagTest(self):
        index = self.ui.tableView.selectedIndexes()
        tagSet = set()
        currentTag = self.prxM.data(index[4])

        for r in range(self.exM.rowCount()):
            v = self.exM.data(self.exM.index(r, 4))
            if len(v) > 0:
                tagSet.add(v)

        atb = AddTagBox(self, currentTag, list(tagSet))
        if atb.exec_() == QDialog.Accepted:
            txt = atb.TE.toPlainText().strip()
            # truncate at 256 characters.
            if len(txt) > 256:
                txt = txt[:256]

            self.prxM.setData(index[4], txt)
            # resize view too
            self.ui.tableView.resizeRowsToContents()

            # send updated tag back to server.
            msg = messenger.SRMsg(
                [
                    "mTAG",
                    self.userName,
                    self.token,
                    self.prxM.data(index[0]),
                    self.prxM.data(index[4]),  # send the tags back too
                ]
            )

        return

    def setFilter(self):
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        self.prxM.filterTags()
