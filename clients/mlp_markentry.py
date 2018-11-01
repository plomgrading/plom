from PyQt5.QtWidgets import QWidget, QPushButton, QGridLayout, QStackedWidget, QLabel, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt


class MarkEntry(QStackedWidget):
    markSetSignal = pyqtSignal(int)
    deltaSetSignal = pyqtSignal(int)

    def __init__(self, maxScore):
        super(MarkEntry, self).__init__()
        self.maxScore = maxScore
        self.currentScore = 0
        self.numButtons = 5
        self.markButtons = {}
        self.redStyle = "border: 2px solid #ff0000; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop: 0 #ff0000, stop: 0.3 #ffcccc, stop: 0.7 #ffcccc, stop: 1 #ff0000);"
        self.greenStyle = "border: 2px solid #008888; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop: 0 #00bbbb, stop: 1 #008888); "

        self.pageC = QWidget()
        self.pageM = QWidget()

        self.addWidget(self.pageC)
        self.addWidget(self.pageM)
        self.setupC()
        self.style = "None"

    def setStyle(self, markStyle):
        # if passed a marking style, then set up accordingly.
        if markStyle == 1:
            self.mtotalB.animateClick()
        elif markStyle == 2:
            self.mupB.animateClick()
        elif markStyle == 3:
            self.mdownB.animateClick()

    def setupC(self):
        grid = QGridLayout()
        self.mupB = QPushButton("Mark Up")
        self.mdownB = QPushButton("Mark Down")
        self.mtotalB = QPushButton("Mark Total")

        grid.addWidget(self.mupB, 1, 1)
        grid.addWidget(self.mdownB, 2, 1)
        grid.addWidget(self.mtotalB, 3, 1)

        self.mupB.clicked.connect(self.setMarkingUp)
        self.mdownB.clicked.connect(self.setMarkingDown)
        self.mtotalB.clicked.connect(self.setMarkingTotal)

        self.scoreL = QLabel("")
        fnt = self.scoreL.font()
        fnt.setPointSize(fnt.pointSize()*2)
        self.scoreL.setFont(fnt)
        self.scoreL.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.scoreL.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.pageC.setLayout(grid)

    def setMarkingUp(self):
        self.setMark(0)
        grid = QGridLayout()
        self.pdmb = QPushButton()

        grid.addWidget(self.scoreL, 0, 0, 1, 2)
        for k in range(0, self.numButtons+1):
            self.markButtons["p{}".format(k)] = QPushButton("+&{}".format(k))
            grid.addWidget(self.markButtons["p{}".format(k)], k//2+1, k % 2, 1, 1)
            self.markButtons["p{}".format(k)].clicked.connect(self.setDeltaMark)
            self.markButtons["p{}".format(k)].setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.pageM.setLayout(grid)
        self.setCurrentWidget(self.pageM)
        self.style = "Up"

    def setMarkingDown(self):
        self.setMark(self.maxScore)
        grid = QGridLayout()
        self.pdmb = QPushButton()

        grid.addWidget(self.scoreL, 0, 0, 1, 2)
        for k in range(1, self.numButtons+1):
            self.markButtons["m{}".format(k)] = QPushButton("-&{}".format(k))
            grid.addWidget(self.markButtons["m{}".format(k)], k//2+1, k % 2, 1, 1)
            self.markButtons["m{}".format(k)].clicked.connect(self.setDeltaMark)
            self.markButtons["m{}".format(k)].setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.pageM.setLayout(grid)
        self.setCurrentWidget(self.pageM)
        self.markSetSignal.emit(self.currentScore)
        self.style = "Down"

    def setMarkingTotal(self):
        grid = QGridLayout()
        self.pmtb = QPushButton()

        for k in range(0, self.maxScore+1):
            self.markButtons["{}".format(k)] = QPushButton("&{}".format(k))
            grid.addWidget(self.markButtons["{}".format(k)], k//3, k % 3)
            self.markButtons["{}".format(k)].clicked.connect(self.setTotalMark)
            self.markButtons["{}".format(k)].setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.pageM.setLayout(grid)
        self.setCurrentWidget(self.pageM)
        self.markSetSignal.emit(self.currentScore)
        self.style = "Total"

    def setDeltaMark(self):
        self.pdmb.setStyleSheet("")
        self.pdmb = self.sender()
        self.pdmb.setStyleSheet(self.greenStyle)
        self.currentDelta = int(self.sender().text().replace('&', ''))
        self.deltaSetSignal.emit(self.currentDelta)

    def setTotalMark(self):
        self.pmtb.setStyleSheet("")
        self.pmtb = self.sender()
        self.pmtb.setStyleSheet(self.greenStyle)
        self.currentScore = int(self.sender().text().replace('&', ''))
        self.markSetSignal.emit(self.currentScore)

    def setMark(self, newScore):
        self.currentScore = newScore
        self.scoreL.setText("{} / {}".format(self.currentScore, self.maxScore))
        self.markSetSignal.emit(self.currentScore)

    def clearButtonStyle(self):
        self.pdmb.setStyleSheet("")
