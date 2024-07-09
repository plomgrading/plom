# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

import platform
from typing import Any, Optional, Union

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from plom import isValidStudentID


class _ErrorMsg(QMessageBox):
    """A simple error message pop-up.

    See also subclasses ``WarnMsg`` and ``InfoMsg``, in order of
    decreasing implied severity.

    Args:
        parent (QWidget): the parent of this dialog.  If you think you
            should pass ``None`` you should think again very carefully.
        txt (str): the main error message.

    Keyword Args:
        details: optionally a potentially large amount of details.  Might
            be hidden by default.  Should be copy-pastable.  Generally
            pre-formatted.
        info: optionally some more details, like an error message or part
            of an error message.  Will be presented smaller or otherwise
            deemphasized.
        info_pre: True by default which means the info text
            is assumed to be preformatted (whitespace, newlines etc will be
            preserved).  Long lines will be wrapped.
    """

    def __init__(
        self,
        parent: Union[QWidget, None],
        txt: str,
        *,
        details: Optional[str] = None,
        info: Optional[str] = None,
        info_pre: bool = True,
    ):
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
        self.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.setDefaultButton(QMessageBox.StandardButton.Ok)
        self.setIcon(QMessageBox.Icon.Critical)


class BigTextEdit(QTextEdit):
    """Just like QTextEdit but wants to be twice as big."""

    def sizeHint(self):
        sz = super().sizeHint()
        sz.setWidth(sz.width() * 2)
        sz.setHeight(sz.height() * 2)
        return sz


class CustomDetailsDialog(QDialog):
    """A dialog with an expanding details field, instead of the Qt builtin options.

    Args:
        parent (QWidget): who should parent this modal dialog.
        summary (str): an text or html summary.

    Keyword Args:
        details: Provide some string of longer details, which can be
            hidden and scrolled.
        details_html: Provide details in HTML instead.
        info: optionally some more details, like an error message or part
            of an error message.  Will be presented smaller or otherwise
            deemphasized.
        info_pre: True by default which means the info text
            is assumed to be preformatted (whitespace, newlines etc will be
            preserved).  Long lines will be wrapped.
        _extra_big: generally be bigger, intended for private use.
    """

    def __init__(
        self,
        parent: Union[None, QWidget],
        summary: str,
        *,
        details: Optional[str] = "",
        details_html: Optional[str] = "",
        info: Optional[str] = None,
        info_pre: bool = True,
        _extra_big: Optional[bool] = None,
    ):
        super().__init__(parent)

        if info:
            if info_pre:
                summary += f'<small><pre style="white-space: pre-wrap;">\n{info}\n</pre></small>'
            else:
                summary += f"<small>{info}</small>"

        lay = QVBoxLayout()

        if details and details_html:
            raise ValueError('Cannot provide both "details" and "details_html"')

        if _extra_big:
            self.details_TE = BigTextEdit()  # type: ignore
        else:
            self.details_TE = QTextEdit()  # type: ignore
        if details:
            self.details_TE.setText(details)
        if details_html:
            self.details_TE.setHtml(details_html)
        self.details_TE.setReadOnly(True)

        s = QLabel(summary)

        if _extra_big:
            # we monkey patch the size hint width from textedit
            sz = self.details_TE.sizeHint()
            sz.setHeight(1)

            def _hack_sizeHint():
                return sz

            setattr(s, "sizeHint", _hack_sizeHint)

        lay.addWidget(s)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        b = QToolButton(text="Details")  # type: ignore
        b.setCheckable(True)
        b.clicked.connect(self.toggle_details)
        buttons.addButton(b, QDialogButtonBox.ButtonRole.ActionRole)
        lay.addWidget(buttons)
        self.setLayout(lay)

        lay.addWidget(buttons)
        lay.addWidget(self.details_TE)
        b.setChecked(False)
        self.details_TE.setVisible(False)
        b.setArrowType(Qt.ArrowType.RightArrow)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        if not details and not details_html:
            b.setVisible(False)
        self.toggle_button = b

        buttons.accepted.connect(self.accept)
        self.setSizeGripEnabled(True)

    def setIcon(self, x):
        # We're somewhat emulating QMessageBox which can set icons
        # TODO: better yet, implement it!
        pass

    def toggle_details(self):
        if self.details_TE.isVisible():
            self.details_TE.setVisible(False)
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        else:
            self.details_TE.setVisible(True)
            self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.adjustSize()


# TODO: Temporary workaround on macOS: after 6.5.4 or 6.6.1/6.6.2 we should
# drop this and let QMessageBox do its job.  Issue #3217.
if platform.system() == "Darwin":
    # on macOS, detailedText of QMessageBox does not scroll (Issue #3217)
    ErrorMsg: Any = CustomDetailsDialog  # type: ignore
else:
    ErrorMsg: Any = _ErrorMsg  # type: ignore


class WarnMsg(ErrorMsg):
    """A simple warning message pop-up."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Icon.Warning)


class InfoMsg(ErrorMsg):
    """A simple warning message pop-up."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Icon.Information)


class BigMessageDialog(CustomDetailsDialog):
    """A dialog for showing lots of stuff, might need scrollbars.

    Args:
        parent (QWidget): who should parent this modal dialog.
        summary (str): an text or html summary.

    Keyword Args:
        details: Provide some string of longer details, which can be
            hidden and scrolled.
        details_html: Provide details in HTML instead.
        info: optionally some more details, like an error message or part
            of an error message.  Will be presented smaller or otherwise
            deemphasized.
        info_pre: True by default which means the info text
            is assumed to be preformatted (whitespace, newlines etc will be
            preserved).  Long lines will be wrapped.
        show: pass True to have the details initially shown.  By default
            they will start hidden.
    """

    def __init__(self, *args, **kwargs):
        show = kwargs.pop("show", None)
        super().__init__(*args, **kwargs, _extra_big=True)
        if show:
            self.toggle_details()


class SimpleQuestion(QMessageBox):
    """A simple message pop-up with yes/no buttons and question icon."""

    def __init__(self, parent, txt, question=None, details=None, icon_pixmap=None):
        super().__init__(parent)
        self.setText(txt)
        if details:
            self.setDetailedText(details)
        if question:
            self.setInformativeText(question)
        if icon_pixmap:
            self.setIconPixmap(icon_pixmap)
        else:
            self.setIcon(QMessageBox.Icon.Question)
        self.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.setDefaultButton(QMessageBox.StandardButton.Yes)

    @classmethod
    def ask(cls, *args, **kwargs):
        return cls(*args, **kwargs).exec()


class WarningQuestion(SimpleQuestion):
    """A simple message pop-up with yes/no buttons and warning icon."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(QMessageBox.Icon.Warning)


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
        self.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.setDefaultButton(QMessageBox.StandardButton.Yes)
        self.setIcon(QMessageBox.Icon.Question)
        self.setCheckBox(self.cb)


class BlankIDBox(QDialog):
    """Ask user what precisely is blank about a paper."""

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
    """Ask user to enter a student ID and student name, with dynamic lookup from a list."""

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
        """Extract both digits and alphabetic bits from input to guess name and student ID.

        Extract the digits from id_name_text and use it to fill the sid-entry.
        Then extract alphabetic from id_name_text and use it to fill the sname-entry.
        """
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
        """Validate the user input, ensuring valid Student ID and non-blank name."""
        self.sid = self.sidLE.text().strip()
        self.sname = self.snameLE.text().strip()
        if not isValidStudentID(self.sid):
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
    """A settings dialog to change some of the Plom Client settings."""

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
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
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
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        flay.addRow(line)

        flay.addRow("Config file:", QLabel("{}".format(cfgfile)))
        tempdir_prefix = "plom_"
        q = QLabel('{}, in subfolders "{}*"'.format(tmpdir, tempdir_prefix))
        q.setWordWrap(True)
        q.setAlignment(Qt.AlignmentFlag.AlignTop)
        flay.addRow("Temporary files:", q)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_options_back(self):
        """Return the options that have been changed by the dialog."""
        return {
            "FOREGROUND": self.checkFore.isChecked(),
            "LogLevel": self.comboLog.currentText(),
            "LogToFile": self.checkLogFile.isChecked(),
        }
