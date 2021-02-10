#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald

"""Start the Plom client."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import datetime
import signal
import os
import sys
import traceback as tblib

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox

from plom import __version__
from plom import Default_Port
from plom.client.chooser import Chooser


# Pop up a dialog for unhandled exceptions and then exit
sys._excepthook = sys.excepthook


def _exception_hook(exctype, value, traceback):
    s = "".join(tblib.format_exception(exctype, value, traceback))
    mb = QMessageBox()
    mb.setText(
        "!! Something unexpected has happened at {}\n\n"
        "Please file a bug and copy-paste the following:\n\n"
        "{}".format(datetime.datetime.now().strftime("%y:%m:%d-%H:%M:%S"), s)
    )
    mb.setStandardButtons(QMessageBox.Ok)
    mb.exec_()
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
        QApplication.exit(42)


def main():
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
        help="""
            Which server to contact, port defaults to {}.
            Also checks the environment variable {} if omitted.
            """.format(
            Default_Port, "PLOM_SERVER"
        ),
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
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_PASSWORD"]
        except KeyError:
            pass
    if not hasattr(args, "user") or not args.user:
        try:
            args.user = os.environ["PLOM_USER"]
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
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
