__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__credits__ = ['Andrew Rechnitzer', 'Colin MacDonald', 'Elvis Cai']
__license__ = "GPLv3"

import asyncio
import json
import os
import ssl
import sys
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit,\
    QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget


# Get ssl ready for communicating with server.
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Usual server defaults.
serverInfo = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}


def getServerInfo():
    """Get server info from file or leave the defaults"""
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open('../resources/serverDetails.json') as data_file:
            serverInfo = json.load(data_file)

# Fire up the asyncio event loop.
loop = asyncio.get_event_loop()


# The async message handler.
async def handle_image_reload(server, message_port, password):
    # Usual asyncio read/write connection.
    reader, writer = await asyncio.open_connection(server, message_port,
                                                   loop=loop, ssl=sslContext)
    # Send the message as json over the connection
    jm = json.dumps(['RIMR', password])
    writer.write(jm.encode())
    writer.write(b'\x00')
    await writer.drain()
    # Wait for the return message.
    data = await reader.read(100)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    # message should be a list [cmd, user, arg1, arg2, etc] - decode it.
    rmesg = json.loads(data.decode())
    # close the connection and return the message.
    writer.close()
    return rmesg


def requestImageReload(server, message_port, password):
    """Send reload groupimages request to server over asyncio connection."""
    rmsg = loop.run_until_complete(handle_image_reload(
        server, message_port, password))
    return rmsg


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
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
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
                self, "Authenticate", "Enter manager password",
                QLineEdit.Password
                )
            # If user clicks okay then send message.
            if ok:
                requestImageReload(serverInfo['server'],
                                   serverInfo['mport'], pwd)


def main():
    getServerInfo()
    app = QApplication(sys.argv)
    iic = AddScans()
    app.exec_()


if __name__ == '__main__':
    main()
