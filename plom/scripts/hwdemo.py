#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

"""Plom script to start a demo server for homework submissions.

Instructions:
  * Run this script
  * In a new terminal, run the Plom Client and connect to localhost.
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path
from random import randint
from shlex import split
import shutil
import subprocess
import tempfile
from warnings import warn

import fitz

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

    if not args.server_dir:
        args.server_dir = Path(tempfile.mkdtemp(prefix="Plom_HWdemo_", dir=Path.cwd()))
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
    print("Server seems to be running, so we move on to uploading")

    # the demo should work even if self-signed keys are used
    os.environ["PLOM_NO_SSL_VERIFY"] = "1"

    if args.port:
        os.environ["PLOM_SERVER"] = f"localhost:{args.port}"
    else:
        os.environ["PLOM_SERVER"] = "localhost"
    os.environ["PLOM_MANAGER_PASSWORD"] = "1234"
    os.environ["PLOM_SCAN_PASSWORD"] = "4567"

    with working_directory(args.server_dir):
        subprocess.check_call(split("plom-create newspec --demo"))
        subprocess.check_call(split("plom-create uploadspec demoSpec.toml"))

    subprocess.check_call(split("plom-create class --demo"))
    subprocess.check_call(split("plom-create rubric --demo"))
    with working_directory(args.server_dir):
        subprocess.check_call(split("plom-create make"))

    # extract solution images
    with working_directory(args.server_dir):
        print("Extract solution images from pdfs")
        subprocess.check_call(split("plom-solutions extract solutionSpec.toml"))

    # upload solution images
    with working_directory(args.server_dir):
        print("Upload solutions to server")
        subprocess.check_call(split("plom-solutions extract --upload"))

    print("Uploading fake scanned data to the server")

    print("Creating fake-scan data")
    with working_directory(args.server_dir):
        # this creates two batches of fake hw - prefixes = hwA and hwB
        subprocess.check_call(split("python3 -m plom.create.homework_scribbler"))

        # TODO: this is fragile, should not hardcode these student numbers!
        A = "semiloose.10433917._.pdf"
        B = "semiloose_10493869.pdf"
        C = "semiloose_number_11015491.pdf"
        D = "semiloose_11_13_51_53.pdf"
        shutil.move("submittedHWByQ/semiloose.10433917._.pdf", A)
        shutil.move("submittedHWByQ/semiloose.10493869._.pdf", B)
        shutil.move("submittedHWByQ/semiloose.11015491._.pdf", C)
        shutil.move("submittedHWByQ/semiloose.11135153._.pdf", D)
        if args.no_scans:
            print(
                "Have not uploaded fake homework scans - you will need to run plom-hwscan manually."
            )
        else:
            print("Uploading fake scanned data to the server")
            print("Processing some individually, with a mix of semiloose uploading")
            subprocess.check_call(split(f"plom-hwscan process {A} 10433917 -q 1,2,3"))
            subprocess.check_call(split(f"plom-hwscan process {B} 10493869 -q all"))
            subprocess.check_call(split(f"plom-hwscan process {C} 11015491 -q all"))
            doc = fitz.open(D)
            qstr = "[[1,2,3],"
            qstr += ",".join(f"[{randint(1,3)}]" for q in range(2, len(doc) + 1))
            qstr += "]"
            doc.close()
            print(f'Using a randomish page->question mapping of "{qstr}"')
            subprocess.check_call(split(f"plom-hwscan process {D} 11135153 -q {qstr}"))

            print("Processing all hw by question submissions.")
            subprocess.check_call(split("plom-hwscan allbyq -y"))
            print("Replacing all missing questions.")
            subprocess.check_call(split("plom-hwscan missing -y"))

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
