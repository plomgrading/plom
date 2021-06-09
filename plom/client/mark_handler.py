# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2019 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020 Colin B. Macdonald

import logging

from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QToolButton,
    QButtonGroup,
    QGridLayout,
    QMenu,
    QSizePolicy,
)


log = logging.getLogger("markhndlr")


class MarkHandler(QWidget):
    def __init__(self, parent, maxScore, markStyle):
        super(MarkHandler, self).__init__()
        self.parent = parent
        # Set max score/mark
        self.maxScore = maxScore
        # Set current score/mark.
        self.currentScore = 0
        # One button for each possible mark, and a dictionary to store them.
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
        self._setStyle(markStyle)
        self.setDeltaButtonMenu()

    def _setStyle(self, markStyle):
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

    def resetAndMaybeChange(self, maxScore, markStyle):
        """Reset score, replace max/style with new values, regen buttons.

        Total - user just clicks the total mark.
        Up - score starts at zero and increments.
        Down - score starts at max and decrements.
        """
        d = {"Total": 1, "Up": 2, "Down": 3}
        if self.maxScore == maxScore and d[self.style] == markStyle:
            if markStyle == 3:
                self.setMark(self.maxScore)
            else:
                self.setMark(0)
            self.updateRelevantDeltaActions()
            return
        log.info("Adjusting for new number or new style")
        for k, x in self.markButtons.items():
            self.ve.removeButton(x)
            self.layout().removeWidget(x)
            x.deleteLater()
        self.markButtons.clear()
        self.currentScore = 0
        self.maxScore = maxScore
        self.markButtons = {}
        self._setStyle(markStyle)
        self.setDeltaButtonMenu()

    def getButtonList(self):
        """Return a list of the buttons"""
        return self.markButtons.values()

    def setMarkingUp(self):
        self.setMark(0)
        grid = self.layout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        ncolumn = min(self.maxScore, 5)

        for k in range(0, self.maxScore + 1):
            b = QToolButton()
            self.markButtons[k] = b
            b.setText("+{}".format(k))
            b.setCheckable(True)
            # b.setAutoExclusive(True)
            grid.addWidget(b, k // ncolumn + 1, k % ncolumn, 1, 1)
            b.clicked.connect(self.setDeltaMark)
            b.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.style = "Up"

    def setMarkingDown(self):
        self.setMark(self.maxScore)
        grid = self.layout()
        # assume our container will deal with margins
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        ncolumn = min(self.maxScore, 5)

        for k in range(0, self.maxScore + 1):
            b = QToolButton()
            self.markButtons[k] = b
            b.setText("-{}".format(k))
            b.setCheckable(True)
            # b.setAutoExclusive(True)
            grid.addWidget(b, k // ncolumn + 1, k % ncolumn, 1, 1)
            b.clicked.connect(self.setDeltaMark)
            b.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

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
            self.markButtons[k] = QPushButton("{}".format(k))
            grid.addWidget(self.markButtons[k], k // ncolumn, k % ncolumn)
            self.markButtons[k].clicked.connect(self.setTotalMark)
            self.markButtons[k].setSizePolicy(
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
        self.markButtons[abs(idelta)].animateClick()

    def unpickleTotal(self, score):
        if (score <= self.maxScore) and (score >= 0) and (self.style == "Total"):
            self.markButtons[score].animateClick()

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
            self.markButtons[delta].animateClick()
        elif self.style == "Down":
            if delta > 0:
                delta = -1
            else:
                delta -= 1
            if abs(delta) > self.maxScore:
                delta = -1
            self.markButtons[-delta].animateClick()

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
            self.markButtons[delta].animateClick()
        elif self.style == "Down":
            if delta > 0:
                delta = 0
            self.markButtons[-delta].animateClick()

    def setDeltaButtonMenu(self):
        if self.style == "Total":
            # mark total - don't set anything
            return
        deltaMenu = QMenu("Set Delta")
        self.deltaActions = {}
        if self.style == "Up":
            # set to mark up
            for k in range(0, self.maxScore + 1):
                self.deltaActions[k] = deltaMenu.addAction("+{}".format(k))
                self.deltaActions[k].triggered.connect(self.markButtons[k].animateClick)
        elif self.style == "Down":
            # set to mark down
            for k in range(0, self.maxScore + 1):
                self.deltaActions[k] = deltaMenu.addAction("-{}".format(k))
                self.deltaActions[k].triggered.connect(self.markButtons[k].animateClick)
        self.parent.ui.deltaButton.setMenu(deltaMenu)
        self.updateRelevantDeltaActions()

    def updateRelevantDeltaActions(self):
        if self.style == "Total":
            return
        elif self.style == "Up":
            for k in range(0, self.maxScore + 1):
                if self.currentScore + k <= self.maxScore:
                    self.deltaActions[k].setEnabled(True)
                    self.markButtons[k].setEnabled(True)
                else:
                    self.deltaActions[k].setEnabled(False)
                    self.markButtons[k].setEnabled(False)
        elif self.style == "Down":
            for k in range(0, self.maxScore + 1):
                if self.currentScore >= k:
                    self.deltaActions[k].setEnabled(True)
                    self.markButtons[k].setEnabled(True)
                else:
                    self.deltaActions[k].setEnabled(False)
                    self.markButtons[k].setEnabled(False)
