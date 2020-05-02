__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QButtonGroup,
    QGridLayout,
    QStackedWidget,
    QLabel,
    QSizePolicy,
)
from PyQt5.QtCore import Qt


class MarkHandler(QWidget):
    def __init__(self, parent, maxScore):
        super(MarkHandler, self).__init__()
        self.parent = parent
        # Set max score/mark
        self.maxScore = maxScore
        # Set current score/mark.
        self.currentScore = 0
        # One button for each possible mark, and a dictionary to store them.
        self.numButtons = self.maxScore
        self.markButtons = {}
        # Styling for buttons
        self.redStyle = (
            "border: 2px solid #ff0000; background: "
            "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop: 0 #ff0000, "
            "stop: 0.3 #ffcccc, stop: 0.7 #ffcccc, stop: 1 #ff0000);"
        )
        # By default we set style to marking-UP.
        self.style = "Up"
        # Keep last delta used
        self.lastDelta = 0
        self.setLayout(QGridLayout())


    def setStyle(self, markStyle):
        """Sets the mark entry style - either total, up or down
        Total - user just clicks the total mark.
        Up - score starts at zero and increments.
        Down - score starts at max and decrements.
        """
        # if passed a marking style, then set up accordingly.
        if markStyle == 1:
            self.setMarkingTotal()
        elif markStyle == 3:
            self.setMarkingDown()
        else:
            # Default to mark-up.
            self.setMarkingUp()
        self.ve = QButtonGroup()
        self.ve.setExclusive(True)
        for s, x in self.markButtons.items():
            self.ve.addButton(x)


    def setMarkingUp(self):
        self.setMark(0)
        grid = self.layout()

        if self.numButtons > 5:
            ncolumn = 3
        else:
            ncolumn = 2

        for k in range(0, self.numButtons + 1):
            self.markButtons["p{}".format(k)] = QPushButton("+{}".format(k))
            self.markButtons["p{}".format(k)].setCheckable(True)
            #self.markButtons["p{}".format(k)].setAutoExclusive(True)
            grid.addWidget(
                self.markButtons["p{}".format(k)], k // ncolumn + 1, k % ncolumn, 1, 1
            )
            self.markButtons["p{}".format(k)].clicked.connect(self.setDeltaMark)
            self.markButtons["p{}".format(k)].setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
            )

        self.style = "Up"

    def setMarkingDown(self):
        self.setMark(self.maxScore)
        grid = self.layout()

        if self.numButtons > 5:
            ncolumn = 3
        else:
            ncolumn = 2

        for k in range(0, self.numButtons + 1):
            self.markButtons["m{}".format(k)] = QPushButton("-{}".format(k))
            self.markButtons["m{}".format(k)].setCheckable(True)
            #self.markButtons["m{}".format(k)].setAutoExclusive(True)
            grid.addWidget(
                self.markButtons["m{}".format(k)], k // ncolumn + 1, k % ncolumn, 1, 1
            )
            self.markButtons["m{}".format(k)].clicked.connect(self.setDeltaMark)
            self.markButtons["m{}".format(k)].setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
            )

        self.parent.totalMarkSet(self.currentScore)
        self.style = "Down"

    def setMarkingTotal(self):
        grid = self.layout()
        self.ptmb = QPushButton()

        if self.maxScore > 5:
            ncolumn = 3
        else:
            ncolumn = 2

        for k in range(0, self.maxScore + 1):
            self.markButtons["{}".format(k)] = QPushButton("{}".format(k))
            grid.addWidget(self.markButtons["{}".format(k)], k // ncolumn, k % ncolumn)
            self.markButtons["{}".format(k)].clicked.connect(self.setTotalMark)
            self.markButtons["{}".format(k)].setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
            )

        self.parent.totalMarkSet(self.currentScore)
        self.style = "Total"

    def setDeltaMark(self):
        self.sender().setChecked(True)
        # yuck, but this will ensure other tools are not checked
        self.parent.ui.deltaButton.setChecked(True)
        self.currentDelta = self.sender().text()
        self.parent.deltaMarkSet(self.currentDelta)

    def setTotalMark(self):
        self.ptmb.setStyleSheet("")
        self.ptmb = self.sender()
        self.ptmb.setStyleSheet(self.redStyle)
        self.currentScore = int(self.sender().text())
        self.parent.totalMarkSet(self.currentScore)

    def setMark(self, newScore):
        self.currentScore = newScore
        self.parent.totalMarkSet(self.currentScore)

    def clearButtonStyle(self):
        # TODO: kill this?  but how to uncheck all in an exclusive group?
        if self.style == "Total":
            pass  # don't clear the styling when marking total.
        else:
            # Try this one wierd trick...
            self.ve.setExclusive(False)
            for k, x in self.markButtons.items():
                x.setChecked(False)
            self.ve.setExclusive(True)

    def loadDeltaValue(self, delta):
        # delta is a string
        idelta = int(delta)
        if abs(idelta) > self.maxScore or self.style == "Total":
            return
        if idelta <= 0 and self.style == "Down":
            self.markButtons["m{}".format(-idelta)].animateClick()
        elif idelta >= 0 and self.style == "Up":
            self.markButtons["p{}".format(idelta)].animateClick()

    def unpickleTotal(self, score):
        if (score <= self.maxScore) and (score >= 0) and (self.style == "Total"):
            self.markButtons["{}".format(score)].animateClick()

    def incrementDelta(self, dlt):
        # dlt is a string, so make int(delta)
        delta = int(dlt)
        if self.style == "Up":
            if delta < 0:
                delta = 0
            else:
                delta += 1
            if delta > self.maxScore:
                delta = 0
            self.markButtons["p{}".format(delta)].animateClick()
        elif self.style == "Down":
            if delta > 0:
                delta = -1
            else:
                delta -= 1
            if abs(delta) > self.maxScore:
                delta = -1
            self.markButtons["m{}".format(-delta)].animateClick()

    def clickDelta(self, dlt):
        # dlt is a string, so make int(delta)
        # be careful if this has been set by a no-delta comment.
        if dlt == ".":
            delta = 0
        else:
            delta = int(dlt)
        if self.style == "Up":
            if delta < 0:
                delta = 0
            self.markButtons["p{}".format(delta)].animateClick()
        elif self.style == "Down":
            if delta > 0:
                delta = 0
            self.markButtons["m{}".format(-delta)].animateClick()
