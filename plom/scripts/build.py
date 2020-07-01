#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom tools for building tests."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import os
from warnings import warn
from textwrap import dedent, wrap

# import tools for dealing with resource files
import pkg_resources

from plom import __version__
from plom import SpecVerifier, SpecParser
from plom import specdir
from plom.produce import process_class_list, upload_classlist
from plom.produce import buildDatabaseAndPapers
from plom.produce import possible_surname_fields, possible_given_name_fields
from plom.produce.demotools import buildDemoSourceFiles

# TODO: relocate https://gitlab.com/plom/plom/-/issues/891
from plom.finish import clear_manager_login


dbfile = os.path.join(specdir, "plom.db")


def checkTomlExtension(fname):
    ext = os.path.splitext(fname)[1]
    if ext == ".toml":
        return fname
    elif len(ext) == 0:
        return fname + ".toml"
    else:
        print(
            'Your specification file name should either have no extension or end in ".toml".'
        )
        exit(1)


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
    sp = SpecParser()
    if sp.spec["numberToName"] > 0:
        print(
            'Your spec indicates that you wish to print named papers.\nPlease process your class list using "plom-build class ".'
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
#
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

    if args.command == "new":
        if args.demo:
            fname = "demoSpec.toml"
        else:
            fname = checkTomlExtension(args.specFile)
        # copy the template spec into place
        createSpecificationFile(fname)
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
        upload_classlist(cl, args.server, args.password)
    elif args.command == "make":
        buildDatabaseAndPapers(args.server, args.password)
    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    else:
        # no command given so print help.
        parser.print_help()


if __name__ == "__main__":
    main()
