__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

import sys
import tempfile
import json
import asyncio
import ssl
from collections import defaultdict
from examviewwindow import ExamViewWindow
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import seaborn as sns

sns.set()  # Sets up seaborn defaults for plots.


server = "localhost"
webdav_port = 41985
message_port = 41984

# # # # # # # # # # # #
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# # # # # # # # # # # #


async def handle_messaging(msg):
    reader, writer = await asyncio.open_connection(
        server, message_port, loop=loop, ssl=sslContext
    )
    jm = json.dumps(msg)
    writer.write(jm.encode())
    # SSL does not support EOF, so send a null byte to indicate the end of the message.
    writer.write(b"\x00")
    await writer.drain()

    data = await reader.read(100)
    terminate = data.endswith(b"\x00")
    data = data.rstrip(b"\x00")
    rmesg = json.loads(
        data.decode()
    )  # message should be a list [cmd, user, arg1, arg2, etc]
    writer.close()
    return rmesg


def SRMsg(msg):
    # print("Sending message {}",format(msg))
    rmsg = loop.run_until_complete(handle_messaging(msg))
    if rmsg[0] == "ACK":
        return rmsg
    elif rmsg[0] == "ERR":
        # print("Some sort of error occurred - didnt get an ACK, instead got ", rmsg)
        msg = errorMessage(rmsg[1])
        msg.exec_()
        return rmsg
    else:
        msg = errorMessage("Something really wrong has happened.")
        self.Close()


class errorMessage(QMessageBox):
    def __init__(self, txt):
        super(errorMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class userHistogram(QDialog):
    def __init__(self, counts):
        QDialog.__init__(self)
        self.setModal(True)
        grid = QGridLayout()
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        grid.addWidget(self.canvas, 1, 1, 4, 4)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        for u in counts.keys():
            uh = sorted(counts[u].items())
            tot = 0
            for x in uh:
                tot += x[1]
            ax.plot(
                [x[0] for x in uh],
                [x[1] / tot for x in uh],
                "o-",
                label="User {}".format(u),
            )
        ax.legend()
        ax.set_xlabel("mark")
        ax.set_ylabel("proportion")

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 99, 99, 1, 1)
        self.setLayout(grid)
        self.show()


class versionHistogram(QDialog):
    def __init__(self, counts):
        QDialog.__init__(self)
        self.setModal(True)
        grid = QGridLayout()
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        grid.addWidget(self.canvas, 1, 1, 4, 4)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        for v in counts.keys():
            vh = sorted(counts[v].items())
            tot = 0
            for x in vh:
                tot += x[1]
            ax.plot(
                [x[0] for x in vh],
                [x[1] / tot for x in vh],
                "o-",
                label="Version {}".format(v),
            )
        ax.legend()
        ax.set_xlabel("mark")
        ax.set_ylabel("proportion")

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 99, 99)
        self.setLayout(grid)
        self.show()


class userProgress(QDialog):
    def __init__(self, counts):
        QDialog.__init__(self)
        self.setModal(True)
        grid = QGridLayout()

        self.ptab = QTableWidget(len(counts) + 1, 5)
        self.ptab.setHorizontalHeaderLabels(
            ["User", "Done", "Progress", "Avg Time", "Total Time"]
        )
        grid.addWidget(self.ptab, 1, 1)

        gb = {}
        r = 1
        mx = 0
        doneTotal = 0
        for k in counts.keys():
            if counts[k][0] > mx:
                mx = counts[k][0]

        for k in counts.keys():
            gb[k] = QProgressBar()
            gb[k].setMaximum(mx)
            gb[k].setValue(counts[k][0])
            gb[k].setFormat("%v")
            self.ptab.setItem(r, 0, QTableWidgetItem(str(k)))
            self.ptab.setItem(r, 1, QTableWidgetItem(str(counts[k][0])))
            self.ptab.setCellWidget(r, 2, gb[k])
            if counts[k][1] > 0:
                self.ptab.setItem(
                    r, 3, QTableWidgetItem(str(counts[k][2] / counts[k][1]))
                )
                self.ptab.setItem(r, 4, QTableWidgetItem(str(counts[k][2])))
            else:
                self.ptab.setItem(r, 3, QTableWidgetItem("."))
                self.ptab.setItem(r, 4, QTableWidgetItem("."))
            doneTotal += counts[k][0]
            r += 1
        self.ptab.setItem(0, 0, QTableWidgetItem("All"))
        self.ptab.setItem(0, 1, QTableWidgetItem(str(doneTotal)))

        self.ptab.resizeColumnsToContents()
        self.ptab.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.ptab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ptab.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 99, 99)
        self.setLayout(grid)
        self.show()


class groupProgress(QDialog):
    def __init__(self, txt, counts):
        QDialog.__init__(self)
        self.setModal(True)
        grid = QGridLayout()

        self.ptab = QTableWidget(len(counts) + 1, 6)
        self.ptab.setHorizontalHeaderLabels(
            [txt, "Total", "Done", "Progress", "Avg Time", "Total Time"]
        )
        grid.addWidget(self.ptab, 1, 1)

        gb = {}
        r = 1
        total = 0
        doneTotal = 0
        for k in counts.keys():
            gb[k] = QProgressBar()
            gb[k].setMaximum(counts[k][0])
            gb[k].setValue(counts[k][1])
            self.ptab.setItem(r, 0, QTableWidgetItem(str(k)))
            self.ptab.setItem(r, 1, QTableWidgetItem(str(counts[k][0])))
            self.ptab.setItem(r, 2, QTableWidgetItem(str(counts[k][1])))
            self.ptab.setCellWidget(r, 3, gb[k])
            if counts[k][1] > 0:
                self.ptab.setItem(
                    r, 4, QTableWidgetItem(str(counts[k][2] / counts[k][1]))
                )
                self.ptab.setItem(r, 5, QTableWidgetItem(str(counts[k][2])))
            else:
                self.ptab.setItem(r, 4, QTableWidgetItem("."))
                self.ptab.setItem(r, 5, QTableWidgetItem("."))

            total += counts[k][0]
            doneTotal += counts[k][1]
            r += 1
        gb[-1] = QProgressBar()
        gb[-1].setMaximum(total)
        gb[-1].setValue(doneTotal)
        self.ptab.setItem(0, 0, QTableWidgetItem("All"))
        self.ptab.setItem(0, 1, QTableWidgetItem(str(total)))
        self.ptab.setItem(0, 2, QTableWidgetItem(str(doneTotal)))
        self.ptab.setCellWidget(0, 3, gb[-1])

        self.ptab.resizeColumnsToContents()
        self.ptab.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.ptab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ptab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 99, 99)
        self.setLayout(grid)
        self.show()


class simpleTableView(QTableView):
    def __init__(self, model):
        QTableView.__init__(self)
        self.setModel(model)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.parent().requestPageImage(self.selectedIndexes()[0])
        else:
            super(QTableView, self).keyPressEvent(event)


class filterComboBox(QComboBox):
    def __init__(self, txt):
        QWidget.__init__(self)
        self.title = txt
        self.addItem(txt)


class examTable(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("../resources/test_marks.db")
        self.db.setHostName("Andrew")
        self.db.setConnectOptions("QSQLITE_OPEN_READONLY")
        self.db.open()
        self.initUI()
        self.loadData()
        self.setFilterOptions()

    def initUI(self):
        grid = QGridLayout()
        self.exM = QSqlTableModel(self, self.db)
        self.exM.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.exM.setTable("groupimage")
        self.exV = simpleTableView(self.exM)

        grid.addWidget(self.exV, 0, 0, 4, 7)

        self.filterGo = QPushButton("Filter Now")
        self.filterGo.clicked.connect(lambda: self.filter())
        grid.addWidget(self.filterGo, 5, 0)
        self.flP = filterComboBox("PageGroup")
        grid.addWidget(self.flP, 5, 2)
        self.flV = filterComboBox("Version")
        grid.addWidget(self.flV, 5, 3)
        self.flS = filterComboBox("Status")
        grid.addWidget(self.flS, 5, 4)
        self.flU = filterComboBox("Marker")
        grid.addWidget(self.flU, 5, 5)
        self.flM = filterComboBox("Mark")
        grid.addWidget(self.flM, 5, 6)

        self.pgprogB = QPushButton("PG progress")
        self.pgprogB.clicked.connect(lambda: self.computePageGroupProgress())
        grid.addWidget(self.pgprogB, 1, 8)
        self.vprogB = QPushButton("V progress")
        self.vprogB.clicked.connect(lambda: self.computeVersionProgress())
        grid.addWidget(self.vprogB, 2, 8)
        self.uprogB = QPushButton("U progress")
        self.uprogB.clicked.connect(lambda: self.computeUserProgress())
        grid.addWidget(self.uprogB, 3, 8)

        self.vhistB = QPushButton("V histogram")
        self.vhistB.clicked.connect(lambda: self.computeVersionHistogram())
        grid.addWidget(self.vhistB, 2, 9)
        self.uhistB = QPushButton("U histogram")
        self.uhistB.clicked.connect(lambda: self.computeUserHistogram())
        grid.addWidget(self.uhistB, 3, 9)

        self.pgImg = ExamViewWindow()
        grid.addWidget(self.pgImg, 0, 10, 20, 20)

        self.setLayout(grid)
        self.show()

    def requestPageImage(self, index):
        rec = self.exM.record(index.row())
        if rec.value("status") == "Marked":
            self.pgImg.updateImage(
                "./markedPapers/{}".format(rec.value("annotatedFile"))
            )
        else:
            self.pgImg.updateImage(rec.value("originalFile"))

    def computeVersionHistogram(self):
        vstats = defaultdict(lambda: defaultdict(int))
        for r in range(self.exM.rowCount()):
            if self.exM.record(r).value("status") == "Marked":
                vstats[self.exM.record(r).value("version")][
                    self.exM.record(r).value("mark")
                ] += 1
        versionHistogram(vstats).exec_()

    def computeUserHistogram(self):
        ustats = defaultdict(lambda: defaultdict(int))
        for r in range(self.exM.rowCount()):
            if self.exM.record(r).value("status") == "Marked":
                ustats[self.exM.record(r).value("user")][
                    self.exM.record(r).value("mark")
                ] += 1
        userHistogram(ustats).exec_()

    def computePageGroupProgress(self):
        pgstats = defaultdict(lambda: [0, 0, 0])
        for r in range(self.exM.rowCount()):
            pgstats[self.exM.record(r).value("pageGroup")][0] += 1
            if self.exM.record(r).value("status") == "Marked":
                pgstats[self.exM.record(r).value("pageGroup")][1] += 1
                pgstats[self.exM.record(r).value("pageGroup")][2] += self.exM.record(
                    r
                ).value("markingTime")
        groupProgress("PageGroup", pgstats).exec_()

    def computeVersionProgress(self):
        vstats = defaultdict(lambda: [0, 0, 0])
        for r in range(self.exM.rowCount()):
            vstats[self.exM.record(r).value("version")][0] += 1
            if self.exM.record(r).value("status") == "Marked":
                vstats[self.exM.record(r).value("version")][1] += 1
                vstats[self.exM.record(r).value("version")][2] += self.exM.record(
                    r
                ).value("markingTime")
        groupProgress("Version", vstats).exec_()

    def computeUserProgress(self):
        ustats = defaultdict(lambda: [0, 0, 0])
        for r in range(self.exM.rowCount()):
            if self.exM.record(r).value("user") == "None":
                continue
            ustats[self.exM.record(r).value("user")][0] += 1
            if self.exM.record(r).value("status") == "Marked":
                ustats[self.exM.record(r).value("user")][1] += 1
                ustats[self.exM.record(r).value("user")][2] += self.exM.record(r).value(
                    "markingTime"
                )
        userProgress(ustats).exec_()

    def getUniqueFromColumn(self, col):
        lst = set()
        query = QSqlQuery(db=self.db)
        query.exec_("select {} from groupimage".format(col))
        while query.next():
            lst.add(str(query.value(0)))
        return sorted(list(lst))

    def loadData(self):
        for c in [0, 2, 3, 6]:
            self.exV.hideColumn(c)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def setFilterOptions(self):
        self.flP.insertItems(1, self.getUniqueFromColumn("pageGroup"))
        self.flV.insertItems(1, self.getUniqueFromColumn("version"))
        self.flS.insertItems(1, self.getUniqueFromColumn("status"))
        self.flU.insertItems(1, self.getUniqueFromColumn("user"))
        self.flM.insertItems(1, self.getUniqueFromColumn("mark"))

    def filter(self):
        flt = []
        if self.flP.currentText() != "PageGroup":
            flt.append("pageGroup='{}'".format(self.flP.currentText()))
        if self.flV.currentText() != "Version":
            flt.append("version='{}'".format(self.flV.currentText()))
        if self.flS.currentText() != "Status":
            flt.append("status='{}'".format(self.flS.currentText()))
        if self.flU.currentText() != "Marker":
            flt.append("user='{}'".format(self.flU.currentText()))
        if self.flM.currentText() != "Mark":
            flt.append("mark='{}'".format(self.flM.currentText()))

        if len(flt) > 0:
            flts = " AND ".join(flt)
        else:
            flts = ""
        self.exM.setFilter(flts)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)


class manager(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        self.extb = examTable()

        grid.addWidget(self.extb, 1, 1, 4, 6)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(lambda: self.close())
        grid.addWidget(self.closeB, 6, 99)

        self.setLayout(grid)
        self.setWindowTitle("Where we are at.")
        self.show()


loop = asyncio.get_event_loop()
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

app = QApplication(sys.argv)
iic = manager()
app.exec_()
