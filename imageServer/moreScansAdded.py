import asyncio
import json
import os
import ssl
import sys
from PyQt5.QtWidgets import QAbstractItemView, QAbstractScrollArea, QApplication, QDialog, QGridLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QSizePolicy

sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False

serverInfo = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}


def getServerInfo():
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open('../resources/serverDetails.json') as data_file:
            serverInfo = json.load(data_file)


loop = asyncio.get_event_loop()


async def handle_image_reload(server, message_port, password):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    jm = json.dumps(['RIMR', password])
    writer.write(jm.encode())
    writer.write(b'\x00')
    await writer.drain()

    data = await reader.read(100)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    rmesg = json.loads(data.decode())  # message should be a list [cmd, user, arg1, arg2, etc]
    writer.close()
    return rmesg


def requestImageReload(server, message_port, password):
    rmsg = loop.run_until_complete(handle_image_reload(server, message_port, password))
    return(rmsg)


class SimpleMessage(QMessageBox):
    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


class AddScans(QWidget):
    def __init__(self):
        super(AddScans, self).__init__()
        self.resize(200, 100)
        closeB = QPushButton("close")
        reloadB = QPushButton("Reload page images")

        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        closeB.setSizePolicy(sizePolicy)
        reloadB.setSizePolicy(sizePolicy)

        closeB.clicked.connect(self.close)
        reloadB.clicked.connect(self.contactServerReload)

        vl = QVBoxLayout()
        vl.addWidget(reloadB)
        vl.addWidget(closeB)
        self.setLayout(vl)
        self.show()

    def contactServerReload(self):
        global serverInfo
        tmp = SimpleMessage("Contact server to reload images?")
        if tmp.exec_() == QMessageBox.Yes:
            pwd, ok = QInputDialog.getText(self, "Authenticate", "Enter manager password", QLineEdit.Password)
            if ok:
                requestImageReload(serverInfo['server'], serverInfo['mport'], pwd)


def main():
    getServerInfo()
    app = QApplication(sys.argv)
    iic = AddScans()
    app.exec_()


if __name__ == '__main__':
    main()
