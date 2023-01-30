#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2022 Edith Coates

"""Start the Plom client."""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import signal
import os
import platform
import sys
import traceback as tblib
from multiprocessing import freeze_support

from PyQt5.QtCore import QTimer, PYQT_VERSION_STR, QT_VERSION_STR
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox

from plom import __version__
from plom import Default_Port
from plom.client import Chooser
from plom.client.useful_classes import ErrorMsg, WarningQuestion
from plom.misc_utils import utc_now_to_string


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
        lines.insert(0, f"Timestamp: {utc_now_to_string()}\n\n")

        txt = f"""<p><b>Something unexpected has happened!</b>
        A partial error message follows.</p>
        <p>(You could consider filing an issue; if you do, please copy-paste
        the text under &ldquo;Show Details&rdquo;.)</p>
        <p>Plom v{__version__}<br />
        PyQt5 {PYQT_VERSION_STR} (Qt {QT_VERSION_STR})<br />
        Python {platform.python_version()},
        {platform.platform()}</p>
        """
        msg = ErrorMsg(
            None,
            txt,
            info=abbrev,
            details="".join(lines),
        )
        msg.setIcon(QMessageBox.Critical)
        msg.exec()
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
    msg = WarningQuestion(
        None, "Caught interrupt signal!", "Do you want to force-quit?"
    )
    msg.setDefaultButton(QMessageBox.No)
    if msg.exec() == QMessageBox.Yes:
        QApplication.exit(42)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run the Plom client. No arguments = run as normal."
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "user",
        type=str,
        nargs="?",
        help="Also checks the environment variable PLOM_USER.",
    )
    parser.add_argument(
        "password",
        type=str,
        nargs="?",
        help="Also checks the environment variable PLOM_PASSWORD.",
    )
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help=f"""
            Which server to contact, port defaults to {Default_Port}.
            Also checks the environment variable PLOM_SERVER if omitted.
        """,
    )
    parser.add_argument(
        "--webplom",
        action="store_true",
        help="""
            Experimental: support connecting to a Django server.
            You can also set the WEBPLOM environment variable.
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-i", "--identifier", action="store_true", help="Run the identifier"
    )
    group.add_argument(
        "-m",
        "--marker",
        const="json",
        nargs="?",
        type=str,
        help="Run the marker. Pass either -m n:k (to run on pagegroup n, version k) or -m (to run on whatever was used last time).",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    args.server = args.server or os.environ.get("PLOM_SERVER")
    args.password = args.password or os.environ.get("PLOM_PASSWORD")
    args.user = args.user or os.environ.get("PLOM_USER")

    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setApplicationName("PlomClient")
    app.setApplicationVersion(__version__)

    signal.signal(signal.SIGINT, sigint_handler)
    add_popup_to_toplevel_exception_handler()

    # create a small timer here, so that we can
    # kill the app with ctrl-c.
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(1000)
    # got this solution from
    # https://machinekoder.com/how-to-not-shoot-yourself-in-the-foot-using-python-qt/

    if args.webplom:
        window = Chooser(app, webplom=True)
    else:
        window = Chooser(app)
    window.show()

    if args.user:
        window.ui.userLE.setText(args.user)
    window.ui.passwordLE.setText(args.password)
    if args.server:
        window.setServer(args.server)

    if args.identifier:
        window.ui.identifyButton.animateClick()
    if args.marker:
        if args.marker != "json":
            pg, v = args.marker.split(":")
            try:
                window.ui.pgSB.setValue(int(pg))
                window.ui.vSB.setValue(int(v))
            except ValueError:
                print(
                    "When you use -m, there should either be no argument, or an argument of the form n:k where n,k are integers."
                )
                sys.exit(43)

        window.ui.markButton.animateClick()
    sys.exit(app.exec())


if __name__ == "__main__":
    # See Issue #2172: needed for Windows + PyInstaller
    freeze_support()
    main()
