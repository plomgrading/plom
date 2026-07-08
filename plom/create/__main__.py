#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2020-2026 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2022 Joey Shi
# Copyright (C) 2022 Edith Coates

"""Plom tools related to producing papers, and setting up servers.

See help for each subcommand or consult online documentation for an
overview of the steps in setting up a server.

Most subcommands communicate with a server, which can be specified
on the command line or by setting environment variables PLOM_SERVER
and PLOM_MANAGER_PASSWORD.
"""

__copyright__ = "Copyright (C) 2020-2026 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import sys
import argparse
import os
from pathlib import Path

from stdiomask import getpass

import plom.create
from plom.create import __version__, Default_Port
from plom.spec_verifier import SpecVerifier
from plom.create import start_messenger
from plom.create import build_extra_page_pdf
from plom.create.demotools import buildDemoSourceFiles
from plom.create import upload_rubrics_from_file, download_rubrics_to_file
from plom.create import upload_demo_rubrics
from plom.create import clear_manager_login


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


def parse_verify_save_spec(fname, *, save=False):
    fname = Path(fname)
    print(f'Parsing and verifying the specification "{fname}"')
    if not fname.exists():
        raise FileNotFoundError(f'Cannot find "{fname}": try "plom-create newspec"?')

    sv = SpecVerifier.from_toml_file(fname)
    sv.verifySpec()
    # TODO: this will create private codes: likely unwanted?
    # sv.checkCodes()
    if not save:
        return
    outfile = Path(".") / "verifiedSpec.toml"
    sv.saveVerifiedSpec(verbose=True, outfile=outfile)


def get_parser():
    def check_non_negative(arg):
        if int(arg) < 0:
            raise ValueError
        return int(arg)

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

    sp_status = sub.add_parser(
        "status",
        help="Status of the server",
        description="Information about the server.",
    )

    sp_newspec = sub.add_parser(
        "newspec",
        help="Create new spec file",
        description="Create new spec file.",
    )
    group = sp_newspec.add_mutually_exclusive_group(required=False)
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
    sp_newspec.add_argument(
        "--demo-num-papers",
        type=int,
        # default=20,  # we want it to give None
        metavar="N",
        help="How many fake exam papers for the demo (defaults to 20 if omitted)",
    )

    spP = sub.add_parser(
        "validatespec",
        help="Check a spec file for validity.",
        description="""Parse and verify a test-specification toml file.""",
    )
    spP.add_argument(
        "specFile",
        nargs="?",
        default="testSpec.toml",
        help="defaults to '%(default)s'.",
    )
    spP.add_argument(
        "--save",
        action="store_true",
        help="""
            By default the verified spec file is not saved.
            Pass this to write it to 'verifiedSpec.toml'.
        """,
    )

    sub.add_parser(
        "extra-pages",
        help="Make an extra pages PDF",
        description="""
            Make a extra-paper PDF for when anyone needs more space.
            NOTE: the resulting file is NOT COMPATIBLE with legacy
            servers (including those in common use in 2023).
        """,
    )

    sp_pred = sub.add_parser(
        "predictions",
        help="Manipulate servers prediction lists",
        description="""
            Before papers are identified, there can exist various predictions
            about which paper goes with which individual.  "Prenamed" is one
            example, where names are pre-printed on the ID sheet.
            Computer vision tools also make predictions based on student ID
            numbers.
        """,
    )
    group = sp_pred.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--predictor",
        type=str,
        metavar="P",
        help="Show all predictions by the predictor P.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Show all predictions.",
    )
    group.add_argument(
        "--erase",
        type=str,
        metavar="P",
        help="""
            Erase all predictions by the predictor P.
            Caution: think carefully before erasing the "prename" predictor.
        """,
    )

    sp_rubric = sub.add_parser(
        "rubric",
        help="Add pre-build rubrics",
        description="""
            Add pre-made rubrics to the server.  Your graders will be able to
            build their own rubrics but if you have premade rubrics you can
            add them here.
            This tool can also dump the current rubrics from a running server.""",
    )
    group = sp_rubric.add_mutually_exclusive_group(required=True)
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

    sp_clear = sub.add_parser(
        "clear",
        help='Clear "manager" login',
        description='Clear "manager" login after a crash or other expected event.',
    )

    for sp in (
        sp_status,
        sp_pred,
        sp_rubric,
        sp_clear,
    ):
        sp.add_argument(
            "-s",
            "--server",
            metavar="SERVER[:PORT]",
            action="store",
            help=f"""
                Which server to contact, port defaults to {Default_Port}.
                Also checks the environment variable PLOM_SERVER if omitted.
            """,
        )
        sp.add_argument(
            "-w",
            "--password",
            type=str,
            help="""
                for the "manager" user, also checks the
                environment variable PLOM_MANAGER_PASSWORD.
            """,
        )

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

    elif args.command == "newspec" or args.command == "new":
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
        print('Creating "sourceVersions/" directory for your test source PDFs.')
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
                f'DEMO: please upload the spec to a server using "plom-cli upload-spec {fname}"'
            )

    elif args.command == "validatespec":
        fname = ensure_toml_extension(args.specFile)
        parse_verify_save_spec(fname, save=args.save)

    elif args.command == "extra-pages":
        print("Building extra page in case students need more space...")
        build_extra_page_pdf(destination_dir=Path.cwd())
        print('See "extra_page.pdf" in the current directory')

    elif args.command == "predictions":
        msgr = start_messenger(args.server, args.password)
        try:
            if args.predictor:
                A = msgr.IDgetPredictionsFromPredictor(args.predictor)
                for k, v in A.items():
                    print(f"{k}: {v}")
            elif args.all:
                A = msgr.IDgetPredictions()
                for k, v in A.items():
                    print(f"{k}: {v}")
            elif args.erase:
                # TODO: send back a number: "42 predictions cleared"?
                msgr.ID_delete_predictions_from_predictor(predictor=args.erase)
                print(f'Erased all predictions by "{args.erase}"')
        finally:
            msgr.closeUser()
            msgr.stop()

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
