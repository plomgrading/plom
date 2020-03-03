__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import sys
import os
import shutil
import shlex
import subprocess
import locale
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)
from resources.uiFiles.ui_launcher import Ui_Launcher

directories = ["build", "finishing", "newServer", "resources"]

directories += ["build/examsToPrint", "build/sourceVersions"]

directories += [
    "newServer/pages",
    "newServer/markedPages",
    "newServer/markedPages/plomFiles",
    "newServer/markedPages/commentFiles",
    "newServer/plomServer",
]

directories += ["clients", "clients/uiFiles", "clients/icons", "clients/cursors"]

files = [
    "resources/plom_exceptions.py",
    "resources/examDB.py",
    "resources/specParser.py",
    "resources/tpv_utils.py",
    "resources/misc_utils.py",
    "resources/predictionlist.csv",
    "resources/pageNotSubmitted.pdf",
    "resources/version.py",
]

files += [
    "build/001_startHere.py",
    "build/002_verifySpec.py",
    "build/003_buildPlomDB.py",
    "build/004_buildPDFs.py",
    "build/004a_buildPDFs_no_names.py",
    "build/004b_buildPDFs_with_names.py",
    "build/cleanAll.py",
    "build/mergeAndCodePages.py",
    "build/template_testSpec.toml",
]

files += [
    "plom/__init__.py",
    "plom/version.py",
    "plom/scan/__init__.py",
    "plom/scan/fasterQRExtract.py",
    "plom/scanMessenger.py",
    "plom/plom_exceptions.py",
    "plom/specParser.py",
    "plom/tpv_utils.py",
    "plom/misc_utils.py",
]

files += [
    "scanCleanAll.py",
    "011_scanningStartHere.py",
    "012_scansToImages.py",
    "013_readQRCodes.py",
    "014_sendPagesToServer.py",
    "015_sendUnknownsToServer.py",
    "016_sendCollisionsToServer.py",
    "019_checkScansStatus.py",
]

files += [
    "newServer/aliceBob.py",
    "newServer/authenticate.py",
    "newServer/latex2png.py",
    "newServer/newServer.py",
    "newServer/pageNotSubmitted.py",
    "newServer/serverSetup.py",
    "newServer/ui_server_setup.py",
    "newServer/userManager.py",
    "newServer/plomServer/routesID.py",
    "newServer/plomServer/routesMark.py",
    "newServer/plomServer/routesReport.py",
    "newServer/plomServer/routesTotal.py",
    "newServer/plomServer/routesUpload.py",
    "newServer/plomServer/routesUserInit.py",
    "newServer/plomServer/serverID.py",
    "newServer/plomServer/serverMark.py",
    "newServer/plomServer/serverReport.py",
    "newServer/plomServer/serverTotal.py",
    "newServer/plomServer/serverUpload.py",
    "newServer/plomServer/serverUserInit.py",
]

files += [
    "clients/annotator.py",
    "clients/client.py",
    "clients/client.spec",
    "clients/examviewwindow.py",
    "clients/identifier.py",
    "clients/key_help.py",
    "clients/marker.py",
    "clients/mark_handler.py",
    "clients/messenger.py",
    "clients/pagescene.py",
    "clients/pageview.py",
    "clients/reorientationwindow.py",
    "clients/totaler.py",
    "clients/test_view.py",
    "clients/useful_classes.py",
    "clients/tools.py",
    "clients/manager.py",
    "clients/managerMessenger.py",
    "clients/collideview.py",
    "clients/discardview.py",
    "clients/selectrectangle.py",
    "clients/unknownpageview.py",
    "clients/plom_exceptions.py",
]

files += [
    "clients/uiFiles/ui_annotator_lhm.py",
    "clients/uiFiles/ui_annotator_rhm.py",
    "clients/uiFiles/ui_chooser.py",
    "clients/uiFiles/ui_identify.py",
    "clients/uiFiles/ui_iic.py",
    "clients/uiFiles/ui_marker.py",
    "clients/uiFiles/ui_test_view.py",
    "clients/uiFiles/ui_totaler.py",
]

files += [
    "clients/icons/comment.svg",
    "clients/icons/comment_up.svg",
    "clients/icons/comment_down.svg",
    "clients/icons/cross.svg",
    "clients/icons/pan.svg",
    "clients/icons/text.svg",
    "clients/icons/delete.svg",
    "clients/icons/pen.svg",
    "clients/icons/tick.svg",
    "clients/icons/line.svg",
    "clients/icons/rectangle.svg",
    "clients/icons/undo.svg",
    "clients/icons/move.svg",
    "clients/icons/redo.svg",
    "clients/icons/zoom.svg",
    "clients/icons/manager_collide.svg",
    "clients/icons/manager_discard.svg",
    "clients/icons/manager_extra.svg",
    "clients/icons/manager_move.svg",
    "clients/icons/manager_none.svg",
    "clients/icons/manager_test.svg",
    "clients/icons/manager_unknown.svg",
]

files += [
    "./clients/cursors/box.png",
    "./clients/cursors/text-comment.png",
    "./clients/cursors/pen.png",
    "./clients/cursors/cross.png",
    "./clients/cursors/delete.png",
    "./clients/cursors/line.png",
    "./clients/cursors/text-delta.png",
    "./clients/cursors/text.png",
    "./clients/cursors/tick.png",
]

files += [
    "finishing/021_startHere.py",
    "finishing/022_check_completed.py",
    "finishing/023_spreadsheet.py",
    "finishing/024_reassemble.py",
    "finishing/024a_reassemble_completed.py",
    "finishing/024b_reassemble_ID_only.py",
    "finishing/10_prepare_coded_return.py",
    "finishing/11_write_to_canvas_spreadsheet.py",
    "finishing/12_archive.py",
    "finishing/coverPageBuilder.py",
    "finishing/return_tools.py",
    "finishing/testReassembler.py",
    "finishing/testReassembler_only_ided.py",
    "finishing/utils.py",
    "finishing/view_test_template.html",
]


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


# class LeftToDo(QDialog):
#     def __init__(self):
#         super(LeftToDo, self).__init__()
#         tasks = {}
#         tasks["0: Right now"] = ["Go to project"]
#         tasks["1: Build"] = [
#             "Name test",
#             "Set number of source tests",
#             "Copy source tests into place",
#             "Set up page grouping",
#             "Set up version choices for groups",
#             "Set total number of tests to produce",
#             "Produce test-files",
#         ]
#         tasks["2: Run the test"] = [
#             "Print tests",
#             "Run test",
#             "Make students very happy",
#             "Scan tests",
#         ]
#         tasks["3: Scan and Group"] = [
#             "Copy test scans to scannedExams",
#             "Convert scans to page images",
#             "Decode page images",
#             "Manual identification" "Check for missing pages",
#             "Group page images into page-groups",
#             "Add an extra pages",
#         ]
#         tasks["4: Image server"] = [
#             "Make sure you have access to two ports",
#             "Set up users",
#             "Get your class list csv",
#             "Run the image server",
#             "Check progress with ID-manager",
#             "Check progress with Marking-manager",
#         ]
#         tasks["5: Clients"] = ["Give markers client apps"]
#         tasks["6: Finishing"] = [
#             "Check tests are completed",
#             "Build cover pages",
#             "Reassemble papers",
#         ]
#         self.setWindowTitle("What to do next")
#         self.setModal(True)
#         grid = QGridLayout()
#
#         self.taskTW = QTreeWidget()
#         self.taskTW.setColumnCount(1)
#         self.taskTW.setHeaderLabel("Tasks")
#         grid.addWidget(self.taskTW, 1, 1, 3, 2)
#         for t in sorted(tasks.keys()):
#             tmp = QTreeWidgetItem(self.taskTW)
#             tmp.setText(0, t)
#             self.taskTW.addTopLevelItem(tmp)
#             for tx in tasks[t]:
#                 tmp2 = QTreeWidgetItem(tmp)
#                 tmp2.setText(0, tx)
#                 tmp.addChild(tmp2)
#
#         self.taskTW.adjustSize()
#
#         self.closeB = QPushButton("Close")
#         grid.addWidget(self.closeB, 4, 4)
#         self.closeB.clicked.connect(self.accept)
#         self.setLayout(grid)


def buildDirs(projPath):
    for dir in directories:
        try:
            os.mkdir(projPath + "/" + dir)
        except os.FileExistsError:
            pass


def copyFiles(projPath):
    for fname in files:
        try:
            shutil.copyfile(fname, projPath + "/" + fname)
        except OSError:
            pass


def buildKey(projPath):
    print("Building new ssl key/certificate for server")
    # Command to generate the self-signed key:
    # openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key \
    #          -nodes -out selfsigned.cert -sha256 -days 1000

    sslcmd = (
        "openssl req -x509 -sha256 -newkey rsa:2048 -keyout "
        "{}/resources/mlp.key -nodes -out "
        "{}/resources/mlp-selfsigned.crt -days 1000 -subj".format(projPath, projPath)
    )
    sslcmd += " '/C={}/ST=./L=./CN=localhost'".format(locale.getdefaultlocale()[0][-2:])
    print(sslcmd)
    subprocess.check_call(shlex.split(sslcmd))


def doThings(projPath):
    try:
        os.mkdir(projPath)
    except FileExistsError:
        msg = SimpleMessage(
            "Directory {} already exists. " "Okay to continue?".format(projPath)
        )
        if msg.exec_() == QMessageBox.No:
            return
    msg = ErrorMessage("Building directories and moving scripts")
    msg.exec_()
    buildDirs(projPath)
    copyFiles(projPath)

    msg = SimpleMessage(
        "Build new ssl-keys (recommended if you have openssl "
        "installed). Otherwise copy ones from repository "
        "(not-recommended)"
    )
    if msg.exec_() == QMessageBox.Yes:
        buildKey(projPath)
    else:
        shutil.copyfile("./resources/mlp.key", projPath + "/resources/mlp.key")
        shutil.copyfile(
            "./resources/mlp-selfsigned.crt", projPath + "/resources/mlp-selfsigned.crt"
        )

    msg = ErrorMessage(
        "Set up server options: IP, ports, the class list "
        "csv file and set manager password"
    )
    msg.exec_()
    cpwd = os.getcwd()
    os.chdir(projPath + "/newServer")
    subprocess.check_call(["python3", "serverSetup.py"])
    os.chdir(cpwd)

    # msg = LeftToDo()
    # msg.exec_()


class ProjectLauncher(QWidget):
    def __init__(self):
        super(ProjectLauncher, self).__init__()
        self.projPath = None
        self.ui = Ui_Launcher()
        self.ui.setupUi(self)

        self.ui.setLocButton.clicked.connect(self.getDirectory)
        self.ui.cancelButton.clicked.connect(self.close)
        self.ui.createButton.clicked.connect(self.createProject)

    def getDirectory(self):
        home = os.getenv("HOME")
        dir = QFileDialog.getExistingDirectory(
            self,
            "Choose a location for your project",
            home,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if os.path.isdir(dir):
            self.ui.directoryLE.setText(dir)

    def createProject(self):
        self.projName = self.ui.nameLE.text()
        if self.projName.isalnum():
            self.projPath = self.ui.directoryLE.text() + "/" + self.projName
            doThings(self.projPath)
        else:
            msg = ErrorMessage("Project name must be an alphanumeric string")
            msg.exec_()
            return
        self.close()


app = QApplication(sys.argv)
window = ProjectLauncher()
window.show()
rv = app.exec_()
sys.exit(rv)
