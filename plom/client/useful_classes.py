__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolButton,
    QVBoxLayout,
)
from plom import isValidStudentNumber


class ErrorMessage(QMessageBox):
    """A simple error message pop-up"""

    def __init__(self, txt):
        super().__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class SimpleMessage(QMessageBox):
    """A simple message pop-up with yes/no buttons."""

    def __init__(self, txt):
        super().__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)


class SimpleMessageCheckBox(QMessageBox):
    """A simple message pop-up with yes/no buttons and a checkbox.

    Args:
        txt: plaintext or html content for the dialog
        cbtxt: optional text for the checkbox else default
    """

    def __init__(self, txt, cbtxt=None):
        super().__init__()
        if cbtxt:
            self.cb = QCheckBox(cbtxt)
        else:
            self.cb = QCheckBox("Don't show this message again")
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)
        self.setCheckBox(self.cb)


class SimpleTableView(QTableView):
    """A table-view widget that emits annotateSignal when
    the user hits enter or return.
    """

    # This is picked up by the marker, lets it know to annotate
    annotateSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(SimpleTableView, self).__init__()
        # User can sort, cannot edit, selects by rows.
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Resize to fit the contents
        self.resizeRowsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def keyPressEvent(self, event):
        # If user hits enter or return, then fire off
        # the annotateSignal, else pass the event on.
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.annotateSignal.emit()
        else:
            super(SimpleTableView, self).keyPressEvent(event)


class SimpleToolButton(QToolButton):
    """Specialise the tool button to be an icon above text."""

    def __init__(self, txt, icon):
        super(SimpleToolButton, self).__init__()
        self.setText(txt)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(QIcon(QPixmap(icon)))
        self.setIconSize(QSize(24, 24))
        self.setMinimumWidth(100)


class NoAnswerBox(QDialog):
    def __init__(self):
        super(NoAnswerBox, self).__init__()
        self.setWindowTitle("Is this answer blank?")
        self.yesNextB = QPushButton("Yes and &Next")
        self.yesDoneB = QPushButton("&Yes")
        self.noB = QPushButton("No, &cancel")
        self.yesNextB.clicked.connect(lambda: self.done(1))
        self.yesDoneB.clicked.connect(lambda: self.done(2))
        self.noB.clicked.connect(self.reject)
        grid = QGridLayout()
        moreinfo = QLabel(
            "<p>Is this answer blank or nearly blank?</p>"
            "<p>Please answer &ldquo;no&rdquo; if there is "
            "<em>any possibility</em> of relevant writing on the page.</p>"
        )
        moreinfo.setWordWrap(True)
        grid.addWidget(moreinfo, 0, 1, 1, 2)
        grid.addWidget(QLabel("advance to next paper"), 1, 2)
        grid.addWidget(QLabel("keep annotating"), 2, 2)
        grid.addWidget(QLabel("keep annotating"), 3, 2)
        grid.addWidget(self.yesNextB, 1, 1)
        grid.addWidget(self.yesDoneB, 2, 1)
        grid.addWidget(self.noB, 3, 1)
        self.setLayout(grid)


class BlankIDBox(QDialog):
    def __init__(self, parent, testNumber):
        super(BlankIDBox, self).__init__()
        self.parent = parent
        self.testNumber = testNumber
        self.setWindowTitle("What is blank on test/paper {}?".format(testNumber))
        grid = QGridLayout()

        grid.addWidget(
            QLabel("Please scan through the whole paper before continuing."), 0, 1, 1, 2
        )

        self.blankB = QPushButton("Whole paper is &blank")
        self.noIDB = QPushButton("&No ID given but not blank")
        self.noB = QPushButton("&Cancel")

        self.blankB.clicked.connect(lambda: self.done(1))
        self.noIDB.clicked.connect(lambda: self.done(2))
        self.noB.clicked.connect(self.reject)
        grid.addWidget(QLabel("Please check to confirm!"), 1, 2)
        grid.addWidget(
            QLabel("There is writing on other this or other pages."),
            2,
            2,
        )
        grid.addWidget(self.blankB, 1, 1)
        grid.addWidget(self.noIDB, 2, 1)
        grid.addWidget(self.noB, 3, 1)
        self.setLayout(grid)


class SNIDBox(QDialog):
    def __init__(self, id_name_text):
        super(SNIDBox, self).__init__()
        self.sidLE = QLineEdit()
        self.snameLE = QLineEdit()
        self.guessInput(id_name_text)
        self.okB = QPushButton("&Done")
        self.cancelB = QPushButton("&Cancel")
        fl = QFormLayout()
        fl.addRow(QLabel("Student ID:"), self.sidLE)
        fl.addRow(QLabel("Student name:"), self.snameLE)
        fl.addRow(self.okB)
        fl.addRow(self.cancelB)
        self.setLayout(fl)

        self.okB.clicked.connect(self.check)
        self.cancelB.clicked.connect(self.reject)
        self.sid = ""
        self.sname = ""

    def guessInput(self, id_name_text):
        """Extract the digits from id_name_text and use it to fill the sid-entry, and then extract alphabetic from id_name_text and use it to fill the sname-entry"""
        sid = ""
        sname = ""
        for c in id_name_text:
            # if it is a number add it to sid
            if c.isdigit():
                sid += c
            # if it is alphabetic add it to sname
            elif c.isalpha() or c in [" ", ","]:
                sname += c
            else:
                pass
        self.sidLE.setText(sid.strip())
        self.snameLE.setText(sname.strip())

    def check(self):
        self.sid = self.sidLE.text().strip()
        self.sname = self.snameLE.text().strip()
        if not isValidStudentNumber(self.sid):
            ErrorMessage("Not a valid student number.").exec_()
            return
        if not self.sname:
            ErrorMessage(
                "<p>Student name should not be blank.</p>"
                "<p>(If you cannot read it, use &ldquo;Unknown&rdquo;.)</p>"
            ).exec_()
            return
        self.accept()


class ClientSettingsDialog(QDialog):
    def __init__(self, s, logdir, cfgfile, tmpdir, comment_file):
        super().__init__()
        # self.parent = parent
        self.setWindowTitle("Plom client options")

        flay = QFormLayout()

        self.comboLog = QComboBox()
        self.comboLog.addItems(["Debug", "Info", "Warning", "Error", "Critical"])
        self.comboLog.setCurrentText(s.get("LogLevel", "Info"))
        flay.addRow("Logging level:", self.comboLog)
        moreinfo = QLabel(
            "(In order of severity; less serious messages will not be logged)"
        )
        flay.addWidget(moreinfo)

        self.checkLogFile = QCheckBox("Log to file (requires restart)")
        self.checkLogFile.setCheckState(
            Qt.Checked if s.get("LogToFile") else Qt.Unchecked
        )
        flay.addWidget(self.checkLogFile)
        flay.addWidget(QLabel("(Logs stored in {})".format(logdir)))

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)

        self.checkFore = QCheckBox("Force foreground upload/downloads")
        self.checkFore.setCheckState(
            Qt.Checked if s.get("FOREGROUND") else Qt.Unchecked
        )
        flay.addWidget(self.checkFore)

        moreinfo = QLabel(
            "By default, Plom does these operations in background threads.\n"
            "Checking this (e.g., for debugging or paranoia) will result in\n"
            "delays between papers."
        )
        # moreinfo.setWordWrap(True)
        flay.addWidget(moreinfo)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)

        self.leftHandMouse = QCheckBox("Left-handed mouse")
        self.leftHandMouse.setCheckState(
            Qt.Checked if s.get("mouse").lower() == "left" else Qt.Unchecked
        )
        flay.addWidget(self.leftHandMouse)

        self.checkSidebarOnRight = QCheckBox("Annotator sidebar on right")
        self.checkSidebarOnRight.setCheckState(
            Qt.Checked if s.get("SidebarOnRight") else Qt.Unchecked
        )
        flay.addWidget(self.checkSidebarOnRight)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)

        self.checkWarnCom = QCheckBox(
            "Warn on insufficient feedback (e.g., no comments)"
        )
        self.checkWarnMark = QCheckBox("Warn if score is inconsistent with annotations")
        flay.addWidget(self.checkWarnCom)
        flay.addWidget(self.checkWarnMark)
        self.checkWarnCom.setCheckState(
            Qt.Checked if s.get("CommentsWarnings") else Qt.Unchecked
        )
        self.checkWarnMark.setCheckState(
            Qt.Checked if s.get("MarkWarnings") else Qt.Unchecked
        )
        if not s.get("POWERUSER"):
            self.checkWarnCom.setEnabled(False)
            self.checkWarnMark.setEnabled(False)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)
        flay.addRow("Config file:", QLabel("{}".format(cfgfile)))
        flay.addRow("Rubrics:", QLabel("{}".format(comment_file)))
        tempdir_prefix = "plom_"
        q = QLabel('{}, in subfolders "{}*"'.format(tmpdir, tempdir_prefix))
        q.setWordWrap(True)
        q.setAlignment(Qt.AlignTop)
        flay.addRow("Temporary files:", q)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def getStuff(self):
        return (
            self.checkFore.checkState() == Qt.Checked,
            self.comboLog.currentText(),
            self.checkLogFile.checkState() == Qt.Checked,
            self.checkWarnCom.checkState() == Qt.Checked,
            self.checkWarnMark.checkState() == Qt.Checked,
            self.leftHandMouse.checkState() == Qt.Checked,
            self.checkSidebarOnRight.checkState() == Qt.Checked,
        )
