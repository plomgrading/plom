__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
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

directories = [
    "resources",
    "pages",
]

# TODO: get from elsewhere
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




def buildDirs(projPath):
    for dir in directories:
        try:
            os.mkdir(projPath + "/" + dir)
        except os.FileExistsError:
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
