#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Plom server management GUI tool."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
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

from plom.manager.manager import Manager
from plom import Default_Port
from plom import __version__
from plom.client.useful_classes import ErrorMessage


# Pop up a dialog for unhandled exceptions and then exit
sys._excepthook = sys.excepthook


def _exception_hook(exctype, value, traceback):
    lines = tblib.format_exception(exctype, value, traceback)
    if len(lines) >= 10:
        abbrev = "".join(["\N{Vertical Ellipsis}\n", *lines[-8:]])
    else:
        abbrev = "".join(lines)
    lines.insert(0, f"Timestamp: {datetime.now()}\n\n")
    ErrorMessage(
        """<p><b>Something unexpected has happened!</b>
        A partial error message is shown below.</p>
        <p>(You could consider filing an issue; if you do, please copy-paste
        the entire text under &ldquo;Show Details&rdquo;.)</p>""",
        info=abbrev,
        details="".join(lines),
    ).exec_()
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = _exception_hook


# in order to have a graceful exit on control-c
# https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co?noredirect=1&lq=1
def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write("\r")
    if (
        QMessageBox.question(
            None,
            "",
            "Are you sure you want to force-quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        == QMessageBox.Yes
    ):
        QApplication.quit()


def main():
    parser = argparse.ArgumentParser(description="Plom management tasks.")
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument("-w", "--password", type=str, help='for the "manager" user')
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help="Which server to contact, port defaults to {}.".format(Default_Port),
    )
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_MANAGER_PASSWORD"]
        except KeyError:
            pass

    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    signal.signal(signal.SIGINT, sigint_handler)

    # create a small timer here, so that we can
    # kill the app with ctrl-c.
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(1000)
    # got this solution from
    # https://machinekoder.com/how-to-not-shoot-yourself-in-the-foot-using-python-qt/

    window = Manager(app)
    window.show()

    window.ui.userLE.setText("manager")
    window.ui.passwordLE.setText(args.password)
    if args.server:
        window.setServer(args.server)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
