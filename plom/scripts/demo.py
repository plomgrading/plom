#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-21 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Victoria Schuster

"""Plom script to start a demo server.

Instructions:
  * Run this script
  * In a new terminal, run the Plom Client and connect to localhost.
"""

__copyright__ = "Copyright (C) 2020-2022 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path
from shlex import split
import subprocess
import tempfile
from warnings import warn

from plom import __version__
from plom import Default_Port
from plom.misc_utils import working_directory
from plom.server import PlomServer


parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
parser.add_argument(
    "server_dir",
    nargs="?",
    help="""The directory containing the filespace to be used by this server.
        It will be created if it does not exist.
        You can specify "." to use the current directory.
        If omitted, a uniquely-named directory will be used.
    """,
)
parser.add_argument(
    "-n",
    "--num-papers",
    type=int,
    # default=20,  # we want it to give None
    metavar="N",
    help="How many fake exam papers for the demo (defaults to 20 if omitted)",
)
parser.add_argument(
    "--port",
    type=int,
    help=f"Which port to use for the demo server ({Default_Port} if omitted)",
)
parser.add_argument(
    "--no-scans",
    action="store_true",
    help="Start demo server but without uploading fake-scans. For testing purposes.",
)


def main():
    args = parser.parse_args()
    print("Plom version {}".format(__version__))

    # TODO: much of this could in theory be replaced by PlomDemoServer

    if not args.server_dir:
        args.server_dir = Path(tempfile.mkdtemp(prefix="Plom_Demo_", dir=Path.cwd()))
    args.server_dir = Path(args.server_dir)
    print(f'Using directory "{args.server_dir}" for the demo')
    if not args.server_dir.exists():
        print(f'Creating directory "{args.server_dir}"')
        args.server_dir.mkdir(exist_ok=True)

    is_empty = not any(args.server_dir.iterdir())
    if not is_empty:
        warn(f"Target directory {args.server_dir} is not empty")
    for f in (
        "specAndDatabase",
        "serverConfiguration",
        "archivedPDFs",
        "pageImages",
        "scanPNGs",
        "pages",
    ):
        if (args.server_dir / f).exists():
            raise RuntimeError(
                f'Directory "{args.server_dir/f}" must not exist for this demo'
            )

    init_cmd = f"plom-server init {args.server_dir}"
    if args.port:
        init_cmd += f" --port {args.port}"
    subprocess.check_call(split(init_cmd))

    with working_directory(args.server_dir):
        subprocess.check_call(split("plom-server users --demo"))

    background_server = PlomServer(basedir=args.server_dir)

    assert background_server.process_is_running(), "has the server died?"
    assert background_server.ping_server(), "cannot ping server, something gone wrong?"
    print("Server seems to be running, so we move on to building tests and uploading")

    # the demo should work even if self-signed keys are used
    os.environ["PLOM_NO_SSL_VERIFY"] = "1"

    if args.port:
        os.environ["PLOM_SERVER"] = f"localhost:{args.port}"
    else:
        os.environ["PLOM_SERVER"] = "localhost"
    os.environ["PLOM_MANAGER_PASSWORD"] = "1234"
    os.environ["PLOM_SCAN_PASSWORD"] = "4567"

    with working_directory(args.server_dir):
        if args.num_papers:
            subprocess.check_call(
                split(f"plom-create new --demo --demo-num-papers {args.num_papers}")
            )
        else:
            subprocess.check_call(split("plom-create new --demo"))
        subprocess.check_call(split("plom-create uploadspec demoSpec.toml"))
    subprocess.check_call(split("plom-create class --demo"))
    subprocess.check_call(split("plom-create rubric --demo"))
    with working_directory(args.server_dir):
        subprocess.check_call(split("plom-create make"))
    # extract solution images
    print("Extract solution images from pdfs")
    with working_directory(args.server_dir):
        subprocess.check_call(split("plom-solutions extract solutionSpec.toml"))

    # upload solution images
    with working_directory(args.server_dir):
        print("Upload solutions to server")
        subprocess.check_call(split("plom-solutions extract --upload"))

    print("Creating fake-scan data")
    with working_directory(args.server_dir):
        subprocess.check_call(split("python3 -m plom.create.exam_scribbler"))

    if args.no_scans:
        print(
            "Have not uploaded fake scan data - you will need to run plom-scan manually."
        )
    else:
        with working_directory(args.server_dir):
            print("Uploading fake scanned data to the server")
            opts = "--no-gamma-shift"
            for f in (
                "fake_scribbled_exams1.pdf",
                "fake_scribbled_exams2.pdf",
                "fake_scribbled_exams3.pdf",
            ):
                subprocess.check_call(split(f"plom-scan process {opts} --demo {f}"))
                subprocess.check_call(split(f"plom-scan upload -u {f}"))

    assert background_server.process_is_running(), "has the server died?"
    assert background_server.ping_server(), "cannot ping server, something gone wrong?"
    print("Server seems to still be running: demo setup is complete")

    print('\n*** Now run "plom-client" ***\n')
    port = args.port if args.port else Default_Port
    print(f"  * Server running on port {port} with PID {background_server.pid}\n")
    print(f"  * Account login info: {args.server_dir / 'userListRaw.csv'}\n")
    # print("  * Press Ctrl-C to stop this demo")
    # background_server.wait()
    input("Press enter when you want to stop the server...")
    background_server.stop()
    print("Server stopped, goodbye!")


if __name__ == "__main__":
    main()
