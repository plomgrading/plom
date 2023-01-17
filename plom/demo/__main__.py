#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Victoria Schuster

"""Plom script to start a demo server.

Instructions:
  * Run this script
  * In a new terminal, run the Plom Client and connect to localhost.


You can reproduce the demo using using various command line tools.
Here we assume the Bash shell on a Unix system.  Open two terminals.
In the first terminal::

    plom-server init mysrv --manager-pw 1234
    plom-server launch mysrv

Now in the second terminal::

    export PLOM_NO_SSL_VERIFY=1
    export PLOM_MANAGER_PASSWORD=1234
    export PLOM_SCAN_PASSWORD=4567

    cd mysrv
    plom-create newspec --demo
    plom-create uploadspec demoSpec.toml
    plom-create users --demo
    cd ..
    plom-create class --demo
    plom-create rubric --demo
    cd mysrv
    plom-create make
    plom-create extra-pages
    plom-solutions extract solutionSpec.toml
    plom-solutions extract --upload
    cd ..

    cd mysrv
    python3 -m plom.create.exam_scribbler
    plom-scan process --demo fake_scribbled_exams1.pdf
    plom-scan upload -u fake_scribbled_exams1
    plom-scan process --demo fake_scribbled_exams2.pdf
    plom-scan upload -u fake_scribbled_exams2
    plom-scan process --demo fake_scribbled_exams3.pdf
    plom-scan upload -u fake_scribbled_exams3
    cd ..
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
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


def get_parser():
    parser = argparse.ArgumentParser(
        description="\n".join(__doc__.split("\n")[0:6]),
        epilog="\n".join(__doc__.split("\n")[6:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
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
        help="""
            Start demo server but without uploading fake-scans. For testing purposes.
            Some scribbled simulated student data is still created (with names
            like `fake_scribbled_exams1.pdf`) but these are not automatically
            uploaded to the server.
            """,
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="""
            Start the demo server long enough to get things running, then stop.
            This is primarily for testing and debugging.
        """,
    )
    parser.add_argument(
        "--in-tree-dev",
        action="store_true",
        help="""
            Developer option.  "plom-demo" changes the current working directory
            and then tries to run ``python3 -m plom.create``.  This will fail
            when running the code in-place.  This option will hack the
            PYTHONPATH env var, adding "." to it.  Don't use unless you're
            experimenting with Plom's source code.
        """,
    )
    return parser


def main():
    parser = get_parser()
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
        "pages",
    ):
        if (args.server_dir / f).exists():
            raise RuntimeError(
                f'Directory "{args.server_dir/f}" must not exist for this demo'
            )

    # Note: if you're reading this code, you can use `plom-server ...`
    # where we use `python3 -m plom.server ...` and similarly for most
    # other commands.
    init_cmd = f"python3 -m plom.server init {args.server_dir} --manager-pw 1234"
    if args.port:
        init_cmd += f" --port {args.port}"
    subprocess.check_call(split(init_cmd))

    if args.in_tree_dev:
        # if running in-place, need python -m to work after changing dir
        paths = os.environ.get("PYTHONPATH", "")
        if paths:
            paths = paths.strip().split(os.pathsep)
        else:
            paths = []
        paths.insert(0, str(Path.cwd().resolve()))
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)
        print(f'hacking PYTHONPATH: {os.environ["PYTHONPATH"]}')

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
                split(
                    f"python3 -m plom.create newspec --demo --demo-num-papers {args.num_papers}"
                )
            )
        else:
            subprocess.check_call(split("python3 -m plom.create newspec --demo"))
        subprocess.check_call(split("python3 -m plom.create uploadspec demoSpec.toml"))
        subprocess.check_call(split("python3 -m plom.create users --demo"))
    subprocess.check_call(split("python3 -m plom.create class --demo"))
    subprocess.check_call(split("python3 -m plom.create rubric --demo"))
    with working_directory(args.server_dir):
        subprocess.check_call(split("python3 -m plom.create make"))
        subprocess.check_call(split("python3 -m plom.create extra-pages"))
    # extract solution images
    print("Extract solution images from pdfs")
    with working_directory(args.server_dir):
        subprocess.check_call(
            split("python3 -m plom.solutions extract solutionSpec.toml")
        )

    # upload solution images
    with working_directory(args.server_dir):
        print("Upload solutions to server")
        subprocess.check_call(split("python3 -m plom.solutions extract --upload"))

    print("Creating fake-scan data")
    with working_directory(args.server_dir):
        subprocess.check_call(split("python3 -m plom.create.exam_scribbler"))
    print(">>>>>>>>>> NOTE <<<<<<<<<<")
    print(
        "Some of the demo papers will belong to extra students who are not on the demo classlist."
    )
    print(
        "This is to mimic the situation in which students from another class/section/time sit your test."
    )

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
                subprocess.check_call(
                    split(f"python3 -m plom.scan process {opts} --demo {f}")
                )
                subprocess.check_call(split(f"python3 -m plom.scan upload -u {f}"))

    assert background_server.process_is_running(), "has the server died?"
    assert background_server.ping_server(), "cannot ping server, something gone wrong?"
    print("Server seems to still be running: demo setup is complete")

    if args.prepare_only:
        print("\n*** We will now stop the demo server...")
        print(f'*** You can run it again with "plom-server launch {args.server_dir}"\n')
    else:
        print('\n*** Now run "plom-client" ***\n')
        port = args.port if args.port else Default_Port
        print(f"  * Server running on port {port} with PID {background_server.pid}\n")
        print(f"  * Account login info: {args.server_dir / 'userListRaw.csv'}\n")
        input("Press enter when you want to stop the server...")
    background_server.stop()
    print("Server stopped, goodbye!")


if __name__ == "__main__":
    main()
