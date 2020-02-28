#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later


import datetime
import argparse
import signal
import sys
import traceback as tblib

from .chooser import *

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


class Plom(QApplication):
    def __init__(self, argv):
        super(Plom, self).__init__(argv)


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


if __name__ == "__main__":
    print("PROBABLY THIS FILE IS DEPRECATED: use scripts/plom-client!")
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

    # Command line arguments (currently undocumented/unsupported)
    # either nothing, or the following
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description="Run the Plom client. No arguments = run as normal."
        )
        parser.add_argument("user", type=str)
        parser.add_argument("password", type=str)
        parser.add_argument(
            "-s",
            "--server",
            metavar="SERVER[:PORT]",
            action="store",
            help="Which server to contact, port defaults to {}.".format(Default_Port),
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "-i", "--identifier", action="store_true", help="Run the identifier"
        )
        group.add_argument(
            "-t", "--totaler", action="store_true", help="Run the totaler"
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

        window.ui.userLE.setText(args.user)
        window.ui.passwordLE.setText(args.password)
        if args.server:
            window.setServer(args.server)

        if args.identifier:
            window.ui.identifyButton.animateClick()
        if args.totaler:
            window.ui.totalButton.animateClick()
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
