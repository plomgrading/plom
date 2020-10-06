#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

"""Plom tools for building tests."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer, Colin B. Macdonald and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import io
import os
from textwrap import dedent, wrap

# import tools for dealing with resource files
import pkg_resources
import pandas

from plom import __version__
from plom import SpecVerifier, SpecParser
from plom import specdir
from plom.produce import process_class_list, get_messenger, upload_classlist
from plom.produce import buildDatabaseAndPapers
from plom.produce import possible_surname_fields, possible_given_name_fields
from plom.produce.demotools import buildDemoSourceFiles

# TODO: relocate https://gitlab.com/plom/plom/-/issues/891
from plom.finish import clear_manager_login


dbfile = os.path.join(specdir, "plom.db")


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


def createSpecificationFile(fname):
    print('Creating specification file from template: "{}"'.format(fname))
    print('  * Please edit the template spec "{}"'.format(fname))
    template = pkg_resources.resource_string("plom", "templateTestSpec.toml")
    with open(fname, "wb") as fh:
        fh.write(template)
    print('Creating "sourceVersions" directory for your test source PDFs.')
    os.makedirs("sourceVersions", exist_ok=True)
    print("  * Please copy your test in as version1.pdf, version2.pdf, etc.")


def parseAndVerifySpecification(fname):
    os.makedirs(specdir, exist_ok=True)
    os.makedirs("sourceVersions", exist_ok=True)
    print('Parsing and verifying the specification "{}"'.format(fname))
    if not os.path.isfile(fname):
        print('Cannot find "{}" - have you run "plom-build create" yet?'.format(fname))
        exit(1)

    sv = SpecVerifier.from_toml_file(fname)
    sv.verifySpec()
    sv.checkCodes()
    sv.saveVerifiedSpec()
    print(
        ">>> Note <<<\n"
        "Before proceeding further, you will need to start the server."
        '\nSee "plom-server --help" for more information on how to get the server up and running.\n'
    )

    sp = SpecParser()
    if sp.spec["numberToName"] > 0:
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
    "specFile", nargs="?", default="testSpec.toml", help="defaults to '%(default)s'.",
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
    "specFile", nargs="?", default="testSpec.toml", help="defaults to '%(default)s'.",
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
spB.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
spB.add_argument("-w", "--password", type=str, help='for the "manager" user')

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
        # copy the template spec into place
        createSpecificationFile(fname)
        if args.demo_num_papers:
            assert args.demo, "cannot specify number of demo paper outside of demo mode"
            classlist_len = pandas.read_csv(
                io.BytesIO(pkg_resources.resource_string("plom", "demoClassList.csv"))
            ).shape[0]
            if args.demo_num_papers > classlist_len:
                # TODO: could make longer classlist on the fly?  Or checkin longer list?
                raise ValueError(
                    "Demo size capped at classlist length of {}".format(classlist_len)
                )
            print("DEMO MODE: adjustng spec for {} tests".format(args.demo_num_papers))
            # TODO: use specParser eventually, or put in createSpecification above
            with open(fname, "r") as f:
                spec = f.read()
            spec = spec.replace(
                "numberToProduce = 20",
                "numberToProduce = {}".format(args.demo_num_papers),
            )
            # half of them, up to length of demo classlist
            num_to_name = min(args.demo_num_papers // 2, classlist_len)
            spec = spec.replace(
                "numberToName = 10", "numberToName = {}".format(num_to_name)
            )
            with open(fname, "w") as f:
                f.write(spec)
        if args.demo:
            print("DEMO MODE: building source files")
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
    elif args.command == "make":
        buildDatabaseAndPapers(args.server, args.password)
    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    else:
        # no command given so print help.
        parser.print_help()


if __name__ == "__main__":
    main()
