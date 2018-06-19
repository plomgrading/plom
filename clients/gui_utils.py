import sys
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QMessageBox, QSpinBox, QPushButton

class ErrorMessage(QMessageBox):
  def __init__(self, txt):
    super(ErrorMessage, self).__init__()
    self.setText(txt)
    self.setStandardButtons(QMessageBox.Ok)

class SimpleMessage(QMessageBox):
  def __init__(self, txt):
    super(SimpleMessage, self).__init__()
    self.setText(txt)
    self.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
    self.setDefaultButton(QMessageBox.Yes)
    fnt = self.font(); fnt.setPointSize( (fnt.pointSize()*3)//2 ); self.setFont( fnt )

class StartUpIDWidget(QDialog):
    def __init__(self):
        super(StartUpIDWidget, self).__init__()
        self.server=""
        self.mport=41984
        self.wport=41985
        self.user=""
        self.pwd=""
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Please enter information")

        self.userL = QLabel("User :")
        self.pwdL = QLabel("Password :")
        self.servL = QLabel("Server location:")
        self.mpL = QLabel("Message port:")
        self.wpL = QLabel("Webdav port:")

        self.userLE = QLineEdit("")
        self.pwdLE = QLineEdit(""); self.pwdLE.setEchoMode(QLineEdit.Password)
        self.servLE = QLineEdit("localhost")
        self.mpSB = QSpinBox(); self.mpSB.setRange(0,65535); self.mpSB.setValue(41984)
        self.wpSB = QSpinBox(); self.wpSB.setRange(0,65535); self.wpSB.setValue(41985)

        self.okB = QPushButton('Accept')
        self.okB.clicked.connect(self.validate)

        grid = QGridLayout()
        grid.addWidget(self.userL,0,1)
        grid.addWidget(self.pwdL,1,1)
        grid.addWidget(self.servL,2,1)
        grid.addWidget(self.mpL,3,1)
        grid.addWidget(self.wpL,4,1)
        grid.addWidget(self.userLE,0,2)
        grid.addWidget(self.pwdLE,1,2)
        grid.addWidget(self.servLE,2,2)
        grid.addWidget(self.mpSB,3,2)
        grid.addWidget(self.wpSB,4,2)
        grid.addWidget(self.okB,5,3)

        self.setLayout(grid)
        self.show()

    def validate(self):
        if(not self.userLE.text().isalnum()):
            return
        if(len(self.userLE.text()) == 0):
            return
        self.close()

    def getValues(self):
        self.user=self.userLE.text()
        self.pwd=self.pwdLE.text()
        self.server=self.servLE.text()
        self.mport=self.mpSB.value()
        self.wport=self.wpSB.value()
        return(self.user, self.pwd, self.server, self.mport, self.wport)


class StartUpMarkerWidget(QDialog):
    def __init__(self):
        super(StartUpMarkerWidget, self).__init__()
        self.server=""
        self.mport=41984
        self.wport=41985
        self.user=""
        self.pagegroup=0
        self.version=0
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Please enter information")

        self.userL = QLabel("User :")
        self.pwdL = QLabel("Password :")
        self.pgL = QLabel("Pagegroup :")
        self.vL = QLabel("Version :")

        self.servL = QLabel("Server location:")
        self.mpL = QLabel("Message port:")
        self.wpL = QLabel("Webdav port:")

        self.userLE = QLineEdit("")
        self.pwdLE = QLineEdit(""); self.pwdLE.setEchoMode(QLineEdit.Password)
        self.pgSB = QSpinBox(); self.pgSB.setRange(1,99); self.pgSB.setValue(1)
        self.vSB = QSpinBox(); self.vSB.setRange(1,99); self.vSB.setValue(1)

        self.servLE = QLineEdit("localhost")
        self.mpSB = QSpinBox(); self.mpSB.setRange(0,65535); self.mpSB.setValue(41984)
        self.wpSB = QSpinBox(); self.wpSB.setRange(0,65535); self.wpSB.setValue(41985)

        self.okB = QPushButton('Accept')
        self.okB.clicked.connect(self.validate)

        grid = QGridLayout()
        grid.addWidget(self.userL,0,1)
        grid.addWidget(self.pwdL,1,1)
        grid.addWidget(self.pgL,2,1)
        grid.addWidget(self.vL,3,1)
        grid.addWidget(self.servL,4,1)
        grid.addWidget(self.mpL,5,1)
        grid.addWidget(self.wpL,6,1)

        grid.addWidget(self.userLE,0,2)
        grid.addWidget(self.pwdLE,1,2)
        grid.addWidget(self.pgSB,2,2)
        grid.addWidget(self.vSB,3,2)
        grid.addWidget(self.servLE,4,2)
        grid.addWidget(self.mpSB,5,2)
        grid.addWidget(self.wpSB,6,2)
        grid.addWidget(self.okB,7,3)

        self.setLayout(grid)
        self.show()

    def validate(self):
        if(not self.userLE.text().isalnum()):
            return
        if(len(self.userLE.text()) == 0):
            return
        self.close()

    def getValues(self):
        self.user=self.userLE.text()
        self.pwd=self.pwdLE.text()
        self.pg=self.pgSB.value()
        self.v=self.vSB.value()
        self.server=self.servLE.text()
        self.mport=self.mpSB.value()
        self.wport=self.wpSB.value()
        # print('returning = ', self.user, self.pwd, str(self.pg).zfill(2), str(self.v), self.server, self.mport, self.wport)
        return(self.user, self.pwd, str(self.pg).zfill(2), str(self.v), self.server, self.mport, self.wport)
