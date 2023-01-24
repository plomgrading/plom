# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2023 Colin B. Macdonald

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableView,
    QToolButton,
    QVBoxLayout,
)

from plom import isValidStudentNumber


class ErrorMsg(QMessageBox):
    """A simple error message pop-up.

    See also subclasses ``WarnMsg`` and ``InfoMsg``, in order of
    decreasing implied severity.

    args:
        parent (QWidget): the parent of this dialog.  If you think you
            should pass ``None`` you should think again very carefully.
        txt (str): the main error message.

    kw-args:
        details (str/None): a potentially large amount of details.  Might
            be hidden by default.  Should be copy-pastable.  Generally
            pre-formatted.
        info (str/None): some more details, like an error message or part
            of an error message.  Will be presented smaller or otherwise
            deemphasized.
        info_pre (bool): True by default which means the info text
            is assumed to be preformatted (whitespace, newlines etc will be
            preserved).  Long lines will be wrapped.
    """

    def __init__(self, parent, txt, details=None, info=None, info_pre=True):
        super().__init__(parent)
        self.setText(txt)
        if details:
            self.setDetailedText(details)
        if info:
            if info_pre:
                self.setInformativeText(
                    f'<small><pre style="white-space: pre-wrap;">\n{info}\n</pre></small>'
                )
            else:
                self.setInformativeText(f"<small>{info}</small>")
        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)
        self.setIcon(QMessageBox.Critical)


class WarnMsg(ErrorMsg):
    """A simple warning message pop-up."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Warning)


class InfoMsg(ErrorMsg):
    """A simple warning message pop-up."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Information)


class SimpleQuestion(QMessageBox):
    """A simple message pop-up with yes/no buttons and question icon."""

    def __init__(self, parent, txt, question=None, details=None):
        super().__init__(parent)
        self.setText(txt)
        if details:
            self.setDetailedText(details)
        if question:
            self.setInformativeText(question)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)
        self.setIcon(QMessageBox.Question)


class WarningQuestion(SimpleQuestion):
    """A simple message pop-up with yes/no buttons and warning icon."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Warning)


class SimpleQuestionCheckBox(QMessageBox):
    """A simple message pop-up with yes/no buttons and a checkbox.

    Args:
        txt: plaintext or html content for the dialog
        cbtxt: optional text for the checkbox else default
    """

    def __init__(self, parent, txt, cbtxt=None):
        super().__init__(parent)
        if cbtxt:
            self.cb = QCheckBox(cbtxt)
        else:
            self.cb = QCheckBox("Don't show this message again")
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.Yes)
        self.setIcon(QMessageBox.Question)
        self.setCheckBox(self.cb)


class SimpleTableView(QTableView):
    """A table-view widget that emits annotateSignal when
    the user hits enter or return.
    """

    # This is picked up by the marker, lets it know to annotate
    annotateSignal = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
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


class BlankIDBox(QDialog):
    def __init__(self, parent, testNumber):
        super().__init__(parent)
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
    def __init__(self, parent, id_name_text):
        super().__init__(parent)
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
            ErrorMsg(self, "Not a valid student number.").exec()
            return
        if not self.sname:
            ErrorMsg(
                self,
                "<p>Student name should not be blank.</p>"
                "<p>(If you cannot read it, use &ldquo;Unknown&rdquo;.)</p>",
            ).exec()
            return
        self.accept()


class ClientSettingsDialog(QDialog):
    def __init__(self, parent, s, logdir, cfgfile, tmpdir):
        super().__init__(parent)
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
        self.checkLogFile.setChecked(s.get("LogToFile", False))
        flay.addWidget(self.checkLogFile)
        flay.addWidget(QLabel("(Logs stored in {})".format(logdir)))

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)

        self.checkFore = QCheckBox("Force foreground upload/downloads")
        self.checkFore.setChecked(s.get("FOREGROUND", False))
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

        self.checkWarnCom = QCheckBox(
            "Warn on insufficient feedback (e.g., no comments)"
        )
        self.checkWarnMark = QCheckBox("Warn if score is inconsistent with annotations")
        flay.addWidget(self.checkWarnCom)
        flay.addWidget(self.checkWarnMark)
        self.checkWarnCom.setChecked(s.get("CommentsWarnings", False))

        self.checkWarnMark.setChecked(s.get("MarkWarnings", False))
        if not s.get("POWERUSER"):
            self.checkWarnCom.setEnabled(False)
            self.checkWarnMark.setEnabled(False)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)
        flay.addRow("Config file:", QLabel("{}".format(cfgfile)))
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
            self.checkFore.isChecked(),
            self.comboLog.currentText(),
            self.checkLogFile.isChecked(),
            self.checkWarnCom.isChecked(),
            self.checkWarnMark.isChecked(),
        )


class AddRemoveTagDialog(QDialog):
    """A dialog for managing the tags of a task.

    Args:
        parent (QWidget): who should parent this modal dialog.
        current_tags (list): the current tags to be laid out for
            deletion.
        tag_choices (list): any explicit choices for new tags, although
            free-form choices can also be made.

    Keyword Args:
        label (str): a short description of what we're tagging, such
            as ``"Paper 7"`` or ``32 questions``.  Used to construct
            dialog titles and prompts.

    Uses the usual `accept()` `reject()` mechanism but on accept you'll need
    to check `.return_values` which is a tuple of `("add", new_tag)` or
    `("remove", tag)`.  In either case the latter is a string.

    Note this dialog does not actually change the tag: the caller needs to
    do that.
    """

    def __init__(self, parent, current_tags, tag_choices, *, label=""):
        super().__init__(parent)

        if label:
            self.from_label = f" from {label}"
        else:
            self.from_label = ""
        self.setWindowTitle(f"Add/remove a tag{self.from_label}")
        self.return_values = None

        flay = QFormLayout()
        # flay = QVBoxLayout

        def remove_func_factory(button, tag):
            def remove_func():
                self.remove_tag(tag)

            return remove_func

        if not current_tags:
            flay.addRow(QLabel("<p><b>No current tags</b></p>"))
        else:
            flay.addRow(QLabel("Current tags:"))
            flay.addItem(
                QSpacerItem(20, 4, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
            )
            for tag in current_tags:
                row = QHBoxLayout()
                row.addItem(QSpacerItem(48, 1))
                row.addWidget(QLabel(f"<big><em>{tag}</em></big>"))
                b = QToolButton()
                b.setText("\N{Erase To The Left}")
                # b.setText("\N{Cross Mark}")
                # b.setText("\N{Multiplication Sign}")
                b.setToolTip(f'Remove tag "{tag}"')
                b.clicked.connect(remove_func_factory(b, tag))
                row.addWidget(b)
                row.addItem(
                    QSpacerItem(
                        48, 1, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum
                    )
                )
                flay.addRow(row)
        flay.addItem(
            QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        )
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        flay.addRow(line)
        flay.addItem(
            QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        )
        CBadd = QComboBox()
        CBadd.setEditable(True)
        CBadd.addItem("")
        CBadd.addItems(tag_choices)
        flay.addRow("Add new tag", CBadd)
        self.CBadd = CBadd

        flay.addItem(
            QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        )

        # TODO: cannot tab to OK
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        buttons.accepted.connect(self.add_tag)
        buttons.rejected.connect(self.reject)
        self.CBadd.setFocus()

    def add_tag(self):
        self.return_values = ("add", self.CBadd.currentText())
        self.accept()

    def remove_tag(self, tag):
        msg = f"<p>Do you want to remove tag &ldquo;{tag}&rdquo;?"
        title = f"Remove tag \u201C{tag}\u201D{self.from_label}?"
        if QMessageBox.question(self, title, msg) != QMessageBox.Yes:
            return
        self.return_values = ("remove", tag)
        self.accept()
