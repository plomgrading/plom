import sys
import os
import locale
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget
from ui_launcher import Ui_Launcher

files = ['build', 'finishing', 'imageServer', 'resources', 'scanAndGroup']
files += ['build/01_construct_a_specification.py', 'build/cleanAll.py', 'build/02_build_tests_from_spec.py', 'build/merge_and_code_pages.py', 'build/buildTestPDFs.py', 'build/testspecification.py']
files += [
'scanAndGroup/03_scans_to_page_images.py', 'scanAndGroup/cleanAll.py', 'scanAndGroup/04_decode_images.py', 'scanAndGroup/extract_qr_and_orient.py', 'scanAndGroup/05_missing_pages.py', 'scanAndGroup/manualPageIdentifier.py', 'scanAndGroup/06_group_pages.py', 'scanAndGroup/testspecification.py']
files += ['imageServer/authenticate.py', 'imageServer/mark_manager.py', 'imageServer/examviewwindow.py', 'imageServer/mark_storage.py', 'imageServer/id_storage.py', 'imageServer/testspecification.py', 'imageServer/identify_manager.py', 'imageServer/userManager.py', 'imageServer/image_server.py']
files += [
'finishing/07_check_completed.py', 'finishing/coverPageBuilder.py', 'finishing/08_build_cover_pages.py', 'finishing/testReassembler.py', 'finishing/09_reassemble.py', 'finishing/testspecification.py'
]

def buildTar():
    flist = " ".join(files)
    os.system("tar -cnf mlp.tar {}".format(flist))

def unTar(projPath):
    os.system("tar -xf mlp.tar --directory {}".format(projPath))

def buildKey(projPath):
    print("Building new ssl key/certificate for server")
    # Command to generate the self-signed key:
    #     openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes -out selfsigned.cert -sha256 -days 1000
    sslcmd = "openssl req -x509 -sha256 -newkey rsa:2048 -keyout {}/mlp.key -nodes -out {}/mlp-selfsigned.crt -days 1000".format(projPath, projPath)
    sslcmd += " -subj \'/C={}/ST=./L=./CN=localhost\'".format(locale.getdefaultlocale()[0][-2:])
    print(sslcmd)
    os.system(sslcmd)


def doThings(projPath):
    buildTar()
    unTar(projPath)
    buildKey(projPath)

class ProjectLauncher(QWidget):
    def __init__(self):
        super(ProjectLauncher, self).__init__()
        self.ui = Ui_Launcher()
        self.ui.setupUi(self)

        self.ui.setLocButton.clicked.connect(self.getDirectory)
        self.ui.cancelButton.clicked.connect(self.close)
        self.ui.createButton.clicked.connect(self.createProject)

    def getDirectory(self):
        home = os.getenv("HOME")
        dir = QFileDialog.getExistingDirectory(self, "Choose a directory for your project", home, QFileDialog.ShowDirsOnly|QFileDialog.DontResolveSymlinks)
        if os.path.isdir(dir):
            self.ui.directoryLE.setText(dir)

    def createProject(self):
        doThings(self.ui.directoryLE.text())
        self.close()

app = QApplication(sys.argv)
window = ProjectLauncher()
window.show()
rv = app.exec_()
sys.exit(rv)
