#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Plom server management GUI tool."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import signal
import os
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QStyleFactory

from plom.manager.manager import Manager
from plom import Default_Port
from plom import __version__
from plom.scripts.client import add_popup_to_toplevel_exception_handler
from plom.scripts.client import sigint_handler


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

    args.server = args.server or os.environ.get("PLOM_SERVER")
    args.password = args.password or os.environ.get("PLOM_MANAGER_PASSWORD")

    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    signal.signal(signal.SIGINT, sigint_handler)
    add_popup_to_toplevel_exception_handler()

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
