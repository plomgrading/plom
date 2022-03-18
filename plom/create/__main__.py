#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2022 Joey Shi

"""Plom tools related to producing papers, and setting up servers.

See help for each subcommand or consult online documentation for an
overview of the steps in setting up a server.
"""

__copyright__ = "Copyright (C) 2020-2022 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import sys
import argparse
import os
from pathlib import Path
from textwrap import dedent, wrap

from stdiomask import getpass

import plom
from plom import __version__
from plom import SpecVerifier
from plom import specdir
from plom.plom_exceptions import PlomExistingDatabase
from plom.create import process_classlist_file, get_demo_classlist, upload_classlist
from plom.create import start_messenger
from plom.create import build_database, build_papers
from plom.create import possible_surname_fields, possible_given_name_fields
from plom.create.demotools import buildDemoSourceFiles
from plom.create import upload_rubrics_from_file, download_rubrics_to_file
from plom.create import upload_demo_rubrics
from plom.create import clear_manager_login
from plom.create import version_map_from_file
from plom.create import save_version_map


def ensure_toml_extension(fname):
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
    raise ValueError('Your specification file should have a ".toml" extension.')


def parse_verify_save_spec(fname, save=True):
    fname = Path(fname)
    print(f'Parsing and verifying the specification "{fname}"')
    if not fname.exists():
        raise FileNotFoundError(f'Cannot find "{fname}": try "plom-create new"?')

    sv = SpecVerifier.from_toml_file(fname)
    sv.verifySpec()
    sv.checkCodes()
    if not save:
        return
    specdir.mkdir(exist_ok=True)
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
            'Your spec indicates that you wish to print named papers.\nWhen the server is running, please process your class list using "plom-create class ".\n'
        )


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(
        dest="command", description="Perform tasks related to building tests."
    )

    sp = sub.add_parser(
        "status",
        help="Status of the server",
        description="Information about the server.",
    )
    sp.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    sp.add_argument("-w", "--password", type=str, help='for the "manager" user')
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
        help="Parse spec file (DEPRECATED)",
        description="""
            Parse, verify and save the test-specification toml file.
            This is (probably) DEPRECATED: consider using
            "plom-create uploadspec" to push spec to an already-running
            server instead.  However, the old workflow still works for
            the time being.
        """,
    )
    spP.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    spP.add_argument(
        "--no-save",
        action="store_true",
        help="""
            By default the verified spec file is written to
            'specAndDatabase/verifiedSpec.toml'.
            Pass this to only check 'specFile' and not save it.
        """,
    )

    spS = sub.add_parser(
        "uploadspec",
        help="Upload spec to server",
        description="Upload exam specification to server.",
    )
    spS.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    spS.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spS.add_argument("-w", "--password", type=str, help='for the "manager" user')

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
    spDB.add_argument(
        "--from-file",
        metavar="FILE",
        help="Read the version map from FILE.  WORK-IN-PROGRESS!",
    )
    spDB.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spDB.add_argument("-w", "--password", type=str, help='for the "manager" user')

    spQVM = sub.add_parser(
        "get-ver-map",
        help="Save question-version map from the database",
        description="""
            The question-version map shows which questions have which
            version for each paper.
            This map is created server-side by the 'make-db' command.
            This .csv file can be used to reconstruct the database in
            case of catastrophe: we recommend keeping a backup copy.
        """,
    )
    spQVM.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    spQVM.add_argument("-w", "--password", type=str, help='for the "manager" user')
    spQVM.add_argument(
        "file",
        nargs="?",
        help="""
            Filename, csv or json format.  Default: 'question_version_map.csv'.
        """,
    )

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
        "-x",
        "--namebox-xpos",
        metavar="X",
        type=float,
        help="""
            Specify horizontal centre of the name/ID box that will be printed
            on named papers, a float from 0 (left) to 100 (right) of the page.
            Defaults to 50.""",
    )
    spB.add_argument(
        "-m",
        "-y",
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

    if args.command == "status":
        plom.create.status(msgr=(args.server, args.password))

    elif args.command == "new":
        if args.demo:
            fname = "demoSpec.toml"
        else:
            fname = ensure_toml_extension(args.specFile)

        if args.demo_num_papers:
            assert args.demo, "cannot specify number of demo paper outside of demo mode"
        if args.demo:
            print("DEMO: creating demo test specification file")
            SpecVerifier.create_demo_template(
                fname, num_to_produce=args.demo_num_papers
            )
            print("DEMO: creating demo solution specification file")
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
                "DEMO: building source files: version1.pdf, version2.pdf, solution1.pdf, solutions2.pdf"
            )
            if not buildDemoSourceFiles(solutions=True):
                sys.exit(1)
            print(
                f'DEMO: please upload the spec to a server using "plom-create uploadspec {fname}"'
            )

    elif args.command == "parse":
        fname = ensure_toml_extension(args.specFile)
        parse_verify_save_spec(fname, not args.no_save)

    elif args.command == "uploadspec":
        fname = ensure_toml_extension(args.specFile)
        sv = SpecVerifier.from_toml_file(fname)
        sv.verifySpec()
        sv.checkCodes()
        print("spec seems ok: we will upload it to the server")
        msgr = start_messenger(args.server, args.password)
        try:
            # TODO: sv.spec versus sv.get_public_spec_dict()?
            # TODO: think about who is supposed to know/generate the privateSeed
            msgr.upload_spec(sv.spec)
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "class":
        if args.demo:
            classlist = get_demo_classlist()
        else:
            classlist = process_classlist_file(args.classlist)
        upload_classlist(classlist, msgr=(args.server, args.password))

    elif args.command == "make-db":
        if args.from_file is None:
            status = build_database(msgr=(args.server, args.password))
        else:
            qvmap = version_map_from_file(args.from_file)
            status = build_database(vermap=qvmap, msgr=(args.server, args.password))
        print(status)

    elif args.command == "get-ver-map":
        f = save_version_map(args.file, msgr=(args.server, args.password))
        print(f"Question-version map saved to {f}")

    elif args.command == "make":
        try:
            status = build_database(msgr=(args.server, args.password))
            print(status)
        except PlomExistingDatabase:
            print("Since we already have a database, move on to making papers")
        build_papers(
            fakepdf=args.no_pdf,
            no_qr=args.without_qr,
            indexToMake=args.number,
            xcoord=args.namebox_xpos,
            ycoord=args.namebox_ypos,
            msgr=(args.server, args.password),
        )

    elif args.command == "rubric":
        msgr = start_messenger(args.server, args.password)
        try:
            if args.demo:
                N = upload_demo_rubrics(msgr=msgr)
                print(f"Uploaded {N} demo rubrics")
            elif args.dump:
                download_rubrics_to_file(Path(args.dump), msgr=msgr)
            else:
                upload_rubrics_from_file(Path(args.rubric_file), msgr=msgr)
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
