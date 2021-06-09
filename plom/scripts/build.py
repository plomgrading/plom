#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

"""Plom tools for building tests."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import json
import os
from pathlib import Path
import sys
from textwrap import dedent, wrap

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import toml

from plom import __version__
from plom import SpecVerifier
from plom import specdir
from plom.produce import process_class_list, get_messenger, upload_classlist
from plom.produce import build_database, build_papers
from plom.produce import possible_surname_fields, possible_given_name_fields
from plom.produce.demotools import buildDemoSourceFiles

# TODO: relocate https://gitlab.com/plom/plom/-/issues/891
from plom.finish import clear_manager_login


def upload_rubrics(msgr, rubrics):
    """Upload a list of rubrics to a server."""
    for rub in rubrics:
        # TODO: some autogen ones are also made by manager?
        if rub.get("username", None) == "HAL":
            continue
        # TODO: ask @arechnitzer about this question_number discrepency
        rub["question"] = rub["question_number"]
        msgr.McreateRubric(rub)


def upload_demo_rubrics(msgr, numquestions=3):
    """Load some demo rubrics and upload to server.

    The demo data is a bit sparsified: we fill in missing pieces and
    multiply over questions.
    """
    rubrics_in = toml.loads(resources.read_text("plom", "demo_rubrics.toml"))
    rubrics_in = rubrics_in["rubric"]
    rubrics = []
    for rub in rubrics_in:
        if not hasattr(rub, "kind"):
            if rub["delta"] == ".":
                rub["kind"] = "neutral"
            elif rub["delta"].startswith("+") or rub["delta"].startswith("-"):
                rub["kind"] = "relative"
            else:
                raise ValueError(f'not sure how to map "kind" for rubric:\n  {rub}')
        # Multiply rubrics w/o question numbers, avoids repetition in demo file
        if not hasattr(rub, "question_number"):
            for q in range(1, numquestions + 1):
                r = rub.copy()
                r["question_number"] = q
                rubrics.append(r)
        else:
            rubrics.append(rub)
    upload_rubrics(msgr, rubrics)
    return len(rubrics)


def checkTomlExtension(fname):
    """Append a .toml extension if not present.

    Args:
        fname (str): a filename.

    Returns:
        str: filename with a .toml extension

    Raises:
        ValueError: filename has incorrect extension (neither blank
           nor `.toml`)
    """
    ext = os.path.splitext(fname)[1]
    if ext == ".toml":
        return fname
    elif len(ext) == 0:
        return fname + ".toml"
    else:
        raise ValueError(
            'Your specification file name should either have no extension or end in ".toml".'
        )


def parseAndVerifySpecification(fname):
    os.makedirs(specdir, exist_ok=True)
    os.makedirs("sourceVersions", exist_ok=True)
    print('Parsing and verifying the specification "{}"'.format(fname))
    if not os.path.isfile(fname):
        print('Cannot find "{}" - try "plom-build new"?'.format(fname))
        exit(1)

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


parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
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
        The classlist can be a .csv file with column headers:
          * id - student ID number
          * studentName - student name in a single field

        The student name can be split into multiple fields; the following names
        will be tried for each header:
          * id
          * {}
          * {}

        Alternatively, give a .csv exported from Canvas (experimental!)
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
        which can be a .toml, .json, or .csv
        (TODO: .csv not yet implemented).
        Defaults to FILE.toml if no extension specified..""",
)
group.add_argument(
    "rubric_file",
    nargs="?",
    help="""
        Upload a pre-build list of rubrics from this file.
        This can be a .json, .toml or .csv file
        (TODO: .csv not yet implemented).""",
)
group.add_argument(
    "--demo",
    action="store_true",
    help="Use auto-generated rubric list.",
)

spClear = sub.add_parser(
    "clear",
    help='Clear "manager" login',
    description='Clear "manager" login after a crash or other expected event.',
)
spClear.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
spClear.add_argument("-w", "--password", type=str, help='for the "manager" user')


def main():
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_MANAGER_PASSWORD"]
        except KeyError:
            pass

    if args.command == "new":
        if args.demo:
            fname = "demoSpec.toml"
        else:
            fname = checkTomlExtension(args.specFile)

        if args.demo_num_papers:
            assert args.demo, "cannot specify number of demo paper outside of demo mode"
        if args.demo:
            print("DEMO MODE: creating demo specification file")
            SpecVerifier.create_demo_template(
                fname, num_to_produce=args.demo_num_papers
            )
        else:
            print('Creating specification file from template: "{}"'.format(fname))
            print('  * Please edit the template spec "{}"'.format(fname))
            SpecVerifier.create_template(fname)

        print('Creating "sourceVersions" directory for your test source PDFs.')
        os.makedirs("sourceVersions", exist_ok=True)
        if not args.demo:
            print("  * Please copy your test in as version1.pdf, version2.pdf, etc.")
        if args.demo:
            print("DEMO MODE: building source files: version1.pdf, version2.pdf")
            if not buildDemoSourceFiles():
                exit(1)
            print('DEMO MODE: continuing as if "parse" command was run...')
            parseAndVerifySpecification(fname)
    elif args.command == "parse":
        # check the file extension
        fname = checkTomlExtension(args.specFile)
        # copy the template spec into place
        parseAndVerifySpecification(fname)
    elif args.command == "class":
        cl = process_class_list(args.classlist, args.demo)
        msgr = get_messenger(args.server, args.password)
        upload_classlist(classlist=cl, msgr=msgr)
        print("Imported classlist of length {}.".format(len(cl)))
        print("First student = {}.".format(cl[0]))
        print("Last student = {}.".format(cl[-1]))

    elif args.command == "make":
        status = build_database(args.server, args.password)
        print(status)
        build_papers(args.server, args.password, args.no_pdf, args.without_qr)

    elif args.command == "rubric":
        msgr = get_messenger(args.server, args.password)
        try:
            if args.demo:
                print("Uploading demo rubrics...")
                N = upload_demo_rubrics(msgr)
                print(f"Uploaded {N} demo rubrics")

            elif args.dump:
                filename = Path(args.dump)
                if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
                    filename = filename.with_suffix(filename.suffix + ".toml")
                print(f'Saving server\'s current rubrics to "{filename}"')
                rubrics = msgr.MgetRubrics()
                if filename.suffix == ".json":
                    with open(filename, "w") as f:
                        json.dump(rubrics, f, indent="  ")
                elif filename.suffix == ".toml":
                    with open(filename, "w") as f:
                        toml.dump({"rubric": rubrics}, f)
                else:
                    raise NotImplementedError(
                        f'Don\'t know how to export to "{filename}"'
                    )
            else:
                filename = Path(args.rubric_file)
                if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
                    filename = filename.with_suffix(filename.suffix + ".toml")
                if filename.suffix == ".json":
                    with open(filename, "r") as f:
                        rubrics = json.load(f)
                elif filename.suffix == ".toml":
                    with open(filename, "r") as f:
                        rubrics = toml.load(f)["rubric"]
                else:
                    raise NotImplementedError(
                        f'Don\'t know how to import from "{filename}"'
                    )
                print(f'Adding {len(rubrics)} rubrics from file "{filename}"')
                upload_rubrics(msgr, rubrics)

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
