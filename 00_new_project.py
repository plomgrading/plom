__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import sys
import os
import shutil
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

directories = ["build", "finishing", "imageServer", "resources", "scanAndGroup"]

directories += ["build/examsToPrint", "build/sourceVersions"]

directories += [
    "scanAndGroup/decodedPages",
    "scanAndGroup/pageImages/",
    "scanAndGroup/readyForMarking",
    "scanAndGroup/scannedExams",
    "scanAndGroup/extraPages/",
]

directories += [
    "imageServer/markedPapers",
    "imageServer/markedPapers/plomFiles",
    "imageServer/markedPapers/commentFiles",
]

directories += ["clients", "clients/uiFiles", "clients/icons"]

directories += [
    "finishing/frontPages",
    "finishing/coverPages",
    "finishing/reassembled/",
    "finishing/reassembled_ID_but_not_marked",
]

files = [
    "resources/testspecification.py",
    "resources/davconf.conf",
    "resources/davconf.yaml",
    "resources/predictionlist.csv",
]

files += [
    "build/01_build_specification_gui.py",
    "build/cleanAll.py",
    "build/editMeToBuildASpec.py",
    "build/02_build_tests_from_spec.py",
    "build/mergeAndCodePages.py",
    "build/buildTestPDFs.py",
    "build/ui_builder.py",
    "build/version_selector_qlist.py",
]

files += [
    "scanAndGroup/03_scans_to_page_images.py",
    "scanAndGroup/cleanAll.py",
    "scanAndGroup/04_decode_images.py",
    "scanAndGroup/extractQRAndOrient.py",
    "scanAndGroup/05_missing_pages.py",
    "scanAndGroup/manualPageIdentifier.py",
    "scanAndGroup/06_group_pages.py",
    "scanAndGroup/06a_group_extra_pages.py",
    "scanAndGroup/testspecification.py",
]

files += [
    "imageServer/authenticate.py",
    "imageServer/examviewwindow.py",
    "imageServer/identify_manager.py",
    "imageServer/identify_reverter.py",
    "imageServer/id_storage.py",
    "imageServer/image_server.py",
    "imageServer/latex2png.py",
    "imageServer/mark_manager.py",
    "imageServer/mark_reverter.py",
    "imageServer/mark_storage.py",
    "imageServer/moreScansAdded.py",
    "imageServer/serverSetup.py",
    "imageServer/total_reverter.py",
    "imageServer/total_storage.py",
    "imageServer/ui_server_setup.py",
    "imageServer/userManager.py",
]

files += [
    "clients/annotator.py",
    "clients/client.py",
    "clients/client.spec",
    "clients/examviewwindow.py",
    "clients/identifier.py",
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
]

files += [
    "clients/uiFiles/ui_annotator_lhm.py",
    "clients/uiFiles/ui_annotator_rhm.py",
    "clients/uiFiles/ui_chooser.py",
    "clients/uiFiles/ui_identify.py",
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
]

files += [
    "finishing/07_check_completed.py",
    "finishing/07alt_check_ID_total.py",
    "finishing/08_build_cover_pages.py",
    "finishing/09_reassemble.py",
    "finishing/09alt_reassembled_ided_but_unmarked.py",
    "finishing/10_prepare_coded_return.py",
    "finishing/11_write_to_canvas_spreadsheet.py",
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


class LeftToDo(QDialog):
    def __init__(self):
        super(LeftToDo, self).__init__()
        tasks = {}
        tasks["0: Right now"] = ["Go to project"]
        tasks["1: Build"] = [
            "Name test",
            "Set number of source tests",
            "Copy source tests into place",
            "Set up page grouping",
            "Set up version choices for groups",
            "Set total number of tests to produce",
            "Produce test-files",
        ]
        tasks["2: Run the test"] = [
            "Print tests",
            "Run test",
            "Make students very happy",
            "Scan tests",
        ]
        tasks["3: Scan and Group"] = [
            "Copy test scans to scannedExams",
            "Convert scans to page images",
            "Decode page images",
            "Manual identification" "Check for missing pages",
            "Group page images into page-groups",
            "Add an extra pages",
        ]
        tasks["4: Image server"] = [
            "Make sure you have access to two ports",
            "Set up users",
            "Get your class list csv",
            "Run the image server",
            "Check progress with ID-manager",
            "Check progress with Marking-manager",
        ]
        tasks["5: Clients"] = ["Give markers client apps"]
        tasks["6: Finishing"] = [
            "Check tests are completed",
            "Build cover pages",
            "Reassemble papers",
        ]
        self.setWindowTitle("What to do next")
        self.setModal(True)
        grid = QGridLayout()

        self.taskTW = QTreeWidget()
        self.taskTW.setColumnCount(1)
        self.taskTW.setHeaderLabel("Tasks")
        grid.addWidget(self.taskTW, 1, 1, 3, 2)
        for t in sorted(tasks.keys()):
            tmp = QTreeWidgetItem(self.taskTW)
            tmp.setText(0, t)
            self.taskTW.addTopLevelItem(tmp)
            for tx in tasks[t]:
                tmp2 = QTreeWidgetItem(tmp)
                tmp2.setText(0, tx)
                tmp.addChild(tmp2)

        self.taskTW.adjustSize()

        self.closeB = QPushButton("Close")
        grid.addWidget(self.closeB, 4, 4)
        self.closeB.clicked.connect(self.accept)
        self.setLayout(grid)


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
    os.system(sslcmd)


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
    os.chdir(projPath + "/imageServer")
    os.system("python3 serverSetup.py")
    os.chdir(cpwd)

    msg = LeftToDo()
    msg.exec_()


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
