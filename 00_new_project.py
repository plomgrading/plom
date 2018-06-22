import sys
import os
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget
from ui_launcher import Ui_Launcher

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
        pass

app = QApplication(sys.argv)
window = ProjectLauncher()
window.show()
rv = app.exec_()
sys.exit(rv)
