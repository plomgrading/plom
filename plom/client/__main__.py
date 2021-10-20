#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao

"""Start the Plom client."""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
from datetime import datetime
import signal
import os
import sys
import traceback as tblib

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox

from plom import __version__
from plom import Default_Port
from plom.client import Chooser
from plom.client.useful_classes import ErrorMessage, WarningQuestion


def add_popup_to_toplevel_exception_handler():
    """Muck around with sys's excepthook to popup dialogs on exception and force exit."""
    # keep reference to the original hook
    sys._excepthook = sys.excepthook

    def exception_hook(exctype, value, traceback):
        lines = tblib.format_exception(exctype, value, traceback)
        if len(lines) >= 10:
            abbrev = "".join(["\N{Vertical Ellipsis}\n", *lines[-8:]])
        else:
            abbrev = "".join(lines)
        lines.insert(0, f"Timestamp: {datetime.now()}\n\n")
        msg = ErrorMessage(
            """<p><b>Something unexpected has happened!</b>
            A partial error message is shown below.</p>
            <p>(You could consider filing an issue; if you do, please copy-paste
            the entire text under &ldquo;Show Details&rdquo;.)</p>""",
            info=abbrev,
            details="".join(lines),
        )
        msg.setIcon(QMessageBox.Critical)
        msg.exec_()
        # call the original hook after our dialog closes
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)

    sys.excepthook = exception_hook


def sigint_handler(*args):
    """Handler for the SIGINT signal.

    This is in order to have a somewhat graceful exit on control-c [1]

    [1] https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co?noredirect=1&lq=1
    """
    sys.stderr.write("\r")
    msg = WarningQuestion("Caught interrupt signal!", "Do you want to force-quit?")
    msg.setDefaultButton(QMessageBox.No)
    if msg.exec_() == QMessageBox.Yes:
        QApplication.exit(42)
