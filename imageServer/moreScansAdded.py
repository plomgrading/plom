__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import requests
import json
import os
import ssl
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


# Get ssl ready for communicating with server.
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Usual server defaults.
serverInfo = {"server": "127.0.0.1", "mport": 41984}

authSession = requests.Session()
authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))


def requestScansReload(server, port, password):
    """Get message handler to send user reload request."""
    try:
        response = authSession.put(
            "https://{}:{}/admin/reloadScans".format(server, port),
            json={"pw": password},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            return False
        else:
            raise Exception(
                "Something nasty has happened. Got return code = {}".format(
                    response.status_code
                )
            )
    except Exception as err:
        print(err)
        return False
    return True


def getServerInfo():
    """Get server info from file or leave the defaults"""
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open("../resources/serverDetails.json") as data_file:
            serverInfo = json.load(data_file)


class errorMessage(QMessageBox):
    def __init__(self, txt):
        super(errorMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class SimpleMessage(QMessageBox):
    """Simple messagebox derivative with message and yes/no buttons."""

    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


class AddScans(QWidget):
    def __init__(self):
        """Fire up a small window with close and reload buttons"""
        super(AddScans, self).__init__()
        self.resize(200, 100)
        closeB = QPushButton("close")
        reloadB = QPushButton("Reload page images")
        # Make sure buttons sized properly.
        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        closeB.setSizePolicy(sizePolicy)
        reloadB.setSizePolicy(sizePolicy)
        # Connect to functions.
        closeB.clicked.connect(self.close)
        reloadB.clicked.connect(self.contactServerReload)
        # Simple vertical layout.
        vl = QVBoxLayout()
        vl.addWidget(reloadB)
        vl.addWidget(closeB)
        self.setLayout(vl)
        self.show()

    def contactServerReload(self):
        """Send reload message to server."""
        global serverInfo
        # Simple popup to ask user.
        tmp = SimpleMessage("Contact server to reload images?")
        if tmp.exec_() == QMessageBox.Yes:
            # Grab manager password from user
            # make sure password is ****-d out.
            pwd, ok = QInputDialog.getText(
                self, "Authenticate", "Enter manager password", QLineEdit.Password
            )
            # If user clicks okay then send message.
            if ok:
                ret = requestScansReload(serverInfo["server"], serverInfo["mport"], pwd)
                if not ret:
                    msg = ErrorMessage("Something went wrong when contacting server.")
                    msg.exec_()


def main():
    getServerInfo()
    app = QApplication(sys.argv)
    iic = AddScans()
    app.exec_()


if __name__ == "__main__":
    main()
