import sys
import os
import json
import mlp_marker
import mlp_identifier
from PyQt5.QtWidgets import QApplication, QWidget, QStyleFactory
from uiFiles.ui_chooser import Ui_Chooser


global tempDirectory, directoryPath
lastTime = {}


def readLastTime():
    global lastTime
    if os.path.isfile("lastTime.json"):
        with open('lastTime.json') as data_file:
            lastTime = json.load(data_file)
    else:
        lastTime["user"] = "adr"
        lastTime["server"] = "localhost"
        lastTime["mport"] = "41984"
        lastTime["wport"] = "41985"
        lastTime["pg"] = 1
        lastTime["v"] = 1


def writeLastTime():
    fh = open("lastTime.json", 'w')
    fh.write(json.dumps(lastTime, indent=4, sort_keys=True))
    fh.close()


class Chooser(QWidget):
    def __init__(self):
        super(Chooser, self).__init__()
        self.runIt = None
        self.marker = None
        self.identifier = None

        self.ui = Ui_Chooser()
        self.ui.setupUi(self)
        self.setLastTime()

        self.ui.markButton.clicked.connect(self.runMarker)
        self.ui.identifyButton.clicked.connect(self.runIDer)
        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.startButton.clicked.connect(self.validate)

    def setLastTime(self):
        readLastTime()
        self.ui.userLE.setText(lastTime["user"])
        self.ui.serverLE.setText(lastTime["server"])
        self.ui.mportSB.setValue(int(lastTime["mport"]))
        self.ui.wportSB.setValue(int(lastTime["wport"]))
        self.ui.pgSB.setValue(int(lastTime["pg"]))
        self.ui.vSB.setValue(int(lastTime["v"]))

    def validate(self):
        if (not self.ui.userLE.text().isalnum()) or (not self.ui.userLE.text()):
            return
        user = self.ui.userLE.text()
        pwd = self.ui.passwordLE.text()
        server = self.ui.serverLE.text()
        mport = self.ui.mportSB.value()
        wport = self.ui.wportSB.value()
        if self.runIt == "Marker":
            pg = str(self.ui.pgSB.value()).zfill(2)
            v = str(self.ui.vSB.value())
            self.marker = mlp_marker.MarkerClient(user, pwd, server, mport, wport, pg, v)
            self.marker.show()
        else:
            self.identifier = mlp_identifier.IDClient(user, pwd, server, mport, wport)
            self.identifier.show()

        self.ui.serverGBox.setEnabled(False)
        self.ui.userGBox.setEnabled(False)
        self.ui.markGBox.setEnabled(False)

        self.ui.startButton.clicked.disconnect(self.validate)
        self.ui.startButton.clicked.connect(self.closeWindow)
        self.ui.startButton.setText("&Finished Task")
        return

    def runMarker(self):
        self.runIt = "Marker"
        self.ui.taskGBox.setEnabled(False)
        self.ui.userGBox.setEnabled(True)
        self.ui.serverGBox.setEnabled(True)
        self.ui.markGBox.setEnabled(True)
        self.ui.startButton.setEnabled(True)
        self.repaint()
        self.ui.userLE.setFocus()

    def runIDer(self):
        self.runIt = "IDer"
        self.ui.taskGBox.setEnabled(False)
        self.ui.userGBox.setEnabled(True)
        self.ui.serverGBox.setEnabled(True)
        self.ui.startButton.setEnabled(True)
        self.repaint()
        self.ui.userLE.setFocus()

    def closeWindow(self):
        lastTime["user"] = self.ui.userLE.text()
        lastTime["server"] = self.ui.serverLE.text()
        lastTime["mport"] = self.ui.mportSB.value()
        lastTime["wport"] = self.ui.wportSB.value()
        lastTime["pg"] = self.ui.pgSB.value()
        lastTime["v"] = self.ui.vSB.value()

        writeLastTime()

        self.close()


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create("Fusion"))

window = Chooser()
window.show()
rv = app.exec_()
sys.exit(rv)
