#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Elizabeth Xiao

"""Plom tools for building tests."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path
from textwrap import dedent, wrap

from stdiomask import getpass

from plom import __version__
from plom import SpecVerifier
from plom import specdir
from plom.plom_exceptions import PlomExistingDatabase
from plom.produce import process_classlist_file, get_demo_classlist, upload_classlist
from plom.produce import get_messenger
from plom.produce import build_database, build_papers
from plom.produce import possible_surname_fields, possible_given_name_fields
from plom.produce.demotools import buildDemoSourceFiles
from plom.produce import upload_rubrics_from_file, download_rubrics_to_file
from plom.produce import upload_demo_rubrics
from plom.produce import clear_manager_login


def checkTomlExtension(fname):
    """Append a .toml extension if not present.

    Args:
        fname (pathlib.Path/str): a filename.

    Returns:
        pathlib.Path: filename with a `.toml` extension.

    Raises:
        ValueError: filename has incorrect extension (neither blank
           nor `.toml`)
    """
    fname = Path(fname)
    if fname.suffix.casefold() == ".toml":
        return fname
    if fname.suffix == "":
        return fname.with_suffix(".toml")
    raise ValueError(
        'Your specification file name should either have no extension or end in ".toml".'
    )


def parseAndVerifySpecification(fname):
    fname = Path(fname)
    specdir.mkdir(exist_ok=True)
    Path("sourceVersions").mkdir(exist_ok=True)
    print(f'Parsing and verifying the specification "{fname}"')
    if not fname.exists():
        raise FileNotFoundError(f'Cannot find "{fname}": try "plom-build new"?')

    sv = SpecVerifier.from_toml_file(fname)
    sv.verifySpec()
    sv.checkCodes()
    sv.saveVerifiedSpec(verbose=True)
    print(
        ">>> Note <<<\n"
        "Before proceeding further, you will need to start the server."
        '\nSee "plom-server --help" for more information on how to get the server up and running.\n'
    )

    spec = SpecVerifier.load_verified()
    if spec["numberToName"] > 0:
        print(
            ">>> Note <<<\n"
            'Your spec indicates that you wish to print named papers.\nWhen the server is running, please process your class list using "plom-build class ".\n'
        )


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(
        dest="command", description="Perform tasks related to building tests."
    )
    #
    spC = sub.add_parser(
        "new", help="Create new spec file", description="Create new spec file."
    )
    group = spC.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Use an auto-generated demo test. **Obviously not for real use**",
    )
    # Add to spC not exclusive group
    spC.add_argument(
        "--demo-num-papers",
        type=int,
        # default=20,  # we want it to give None
        metavar="N",
        help="How many fake exam papers for the demo (defaults to 20 if omitted)",
    )

    spP = sub.add_parser(
        "parse",
        help="Parse spec file",
        description="Parse and verify the test-specification toml file.",
    )
    spP.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )

    #
    spL = sub.add_parser(
        "class",
        help="Read in a classlist",
        description="Get student names/numbers from csv, process, and upload to server.",
        epilog=dedent(
            """
            The classlist can be a .csv file exported from Canvas (specifically,
            Canvas -> Grades -> Actions -> Export).  Plom will do some light sanity
            checking such as dropping names like "Test Student".

            Alternatively, the classlist can be a .csv file with column headers:
              * id - student ID number
              * studentName - student name in a single field

            The student name can be split into multiple fields; the following names
            will be tried for each header:
              * id
              * {}
              * {}
            """
        ).format(
            "\n    ".join(wrap(", ".join(possible_surname_fields), 72)),
            "\n    ".join(wrap(", ".join(possible_given_name_fields), 72)),
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    spL.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spL.add_argument("-w", "--password", type=str, help='for the "manager" user')
    group = spL.add_mutually_exclusive_group(required=True)
    group.add_argument("classlist", nargs="?", help="filename in csv format")
    group.add_argument(
        "--demo",
        action="store_true",
        help="Use auto-generated classlist. **DO NOT USE ON REAL SERVER**",
    )

    spDB = sub.add_parser(
        "make-db",
        help="Populate the database",
        description="""
            See "make" below, but here only the database is populated and
            no papers will be built.  You can then call "make" later.""",
    )
    spDB.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spDB.add_argument("-w", "--password", type=str, help='for the "manager" user')

    spB = sub.add_parser(
        "make",
        help="Make the PDFs",
        description="""
            Build papers and database from the test specification.  Based on the
            spec, some of the papers may have names printed on them from the
            classlist ("pre-named") and the remainder will be blank.""",
    )
    spB.add_argument(
        "--no-pdf",
        action="store_true",
        help="Do not generate real PDFs - instead generate empty files.",
    )
    spB.add_argument(
        "--without-qr",
        action="store_true",
        help="Produce PDFs without QR codes and staple-corner indicators.",
    )
    spB.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spB.add_argument("-w", "--password", type=str, help='for the "manager" user')
    spB.add_argument(
        "-n", "--number", type=int, help="used for building a specific paper number"
    )
    spB.add_argument(
        "-m",
        "--namebox-ypos",
        metavar="Y",
        type=float,
        help="""
            Specify vertical location of the name/ID that will be printed on
            named papers, a float from 0 (top) to 100 (bottom) of the
            page.
            Defaults to 42.5 (for historical reasons!)""",
    )

    sp = sub.add_parser(
        "rubric",
        help="Add pre-build rubrics",
        description="""
            Add pre-made rubrics to the server.  Your graders will be able to
            build their own rubrics but if you have premade rubrics you can
            add them here or by using the plom-manager tool.
            This tool can also dump the current rubrics from a running server.""",
    )
    sp.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    sp.add_argument("-w", "--password", type=str, help='for the "manager" user')
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dump",
        type=str,
        metavar="FILE",
        help="""Dump the current rubrics from SERVER into FILE,
            which can be a .toml, .json, or .csv file.
            Defaults to FILE.toml if no extension specified..""",
    )
    group.add_argument(
        "rubric_file",
        nargs="?",
        help="""
            Upload a pre-build list of rubrics from this file.
            This can be a .json, .toml or .csv file.""",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Upload an auto-generated rubric list for demos.",
    )

    spClear = sub.add_parser(
        "clear",
        help='Clear "manager" login',
        description='Clear "manager" login after a crash or other expected event.',
    )
    spClear.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spClear.add_argument("-w", "--password", type=str, help='for the "manager" user')

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "server"):
        args.server = args.server or os.environ.get("PLOM_SERVER")

    if hasattr(args, "password"):
        args.password = args.password or os.environ.get("PLOM_MANAGER_PASSWORD")
        if not args.password:
            args.password = getpass('Please enter the "manager" password: ')

    if args.command == "new":
        if args.demo:
            fname = "demoSpec.toml"
        else:
            fname = checkTomlExtension(args.specFile)

        if args.demo_num_papers:
            assert args.demo, "cannot specify number of demo paper outside of demo mode"
        if args.demo:
            print("DEMO MODE: creating demo test specification file")
            SpecVerifier.create_demo_template(
                fname, num_to_produce=args.demo_num_papers
            )
            print("DEMO MODE: creating demo solution specification file")
            SpecVerifier.create_demo_solution_template("solutionSpec.toml")

        else:
            print('Creating specification file from template: "{}"'.format(fname))
            print('  * Please edit the template spec "{}"'.format(fname))
            SpecVerifier.create_template(fname)
            print("Creating solution specification file template = solutionSpec.toml")
            print(
                "  **Optional** - Please edit the template solution spec if you are including solutions in your workflow."
            )
            SpecVerifier.create_solution_template("solutionSpec.toml")
        print('Creating "sourceVersions" directory for your test source PDFs.')
        Path("sourceVersions").mkdir(exist_ok=True)
        if not args.demo:
            print("  * Please copy your test in as version1.pdf, version2.pdf, etc.")
        if args.demo:
            print(
                "DEMO MODE: building source files: version1.pdf, version2.pdf, solution1.pdf, solutions2.pdf"
            )
            if not buildDemoSourceFiles(solutions=True):
                exit(1)
            print('DEMO MODE: continuing as if "parse" command was run...')
            parseAndVerifySpecification(fname)
    elif args.command == "parse":
        fname = checkTomlExtension(args.specFile)
        # copy the template spec into place
        parseAndVerifySpecification(fname)
    elif args.command == "class":
        if args.demo:
            classlist = get_demo_classlist()
        else:
            classlist = process_classlist_file(args.classlist)
        upload_classlist(classlist, args.server, args.password)

    elif args.command == "make-db":
        status = build_database(args.server, args.password)
        print(status)

    elif args.command == "make":
        try:
            status = build_database(args.server, args.password)
            print(status)
        except PlomExistingDatabase:
            print("Since we already have a database, move on to making papers")
        try:
            build_papers(
                args.server,
                args.password,
                fakepdf=args.no_pdf,
                no_qr=args.without_qr,
                indexToMake=args.number,
                ycoord=args.namebox_ypos,
            )
        except ValueError as err:
            print(f"A value error - {err}")
        except Exception as err:
            print(f"Some other sort of error - {err}")

    elif args.command == "rubric":
        msgr = get_messenger(args.server, args.password)
        try:
            if args.demo:
                N = upload_demo_rubrics(msgr)
                print(f"Uploaded {N} demo rubrics")
            elif args.dump:
                download_rubrics_to_file(msgr, Path(args.dump))
            else:
                upload_rubrics_from_file(msgr, Path(args.rubric_file))
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    else:
        # no command given so print help.
        parser.print_help()


if __name__ == "__main__":
    main()
