#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom tools for building tests."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import os
import shutil

# import tools for dealing with resource files
import pkg_resources

from plom import SpecVerifier, SpecParser
from plom import specdir
from plom.produce import buildAllPapers, confirmProcessed, confirmNamed
from plom.produce import paperdir
from plom.produce import processClasslist
from plom.produce.demotools import buildDemoSourceFiles


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

    sv = SpecVerifier(fname)
    sv.verifySpec()
    sv.checkCodes()
    sv.saveVerifiedSpec()
    sp = SpecParser()
    if sp.spec["numberToName"] > 0:
        print(
            'Your spec indicates that you wish to print named papers.\nPlease process your class list using "plom-build class ".'
        )


def buildDatabase(spec):
    from plom.produce import buildPlomDB

    if os.path.isfile(dbfile):
        print("Database already exists - aborting.")
        exit(1)

    print("Creating plom database")
    buildPlomDB.buildExamDatabase(spec, dbfile)
    print("Database created successfully")


def buildBlankPapers(spec):
    print("Building blank papers")
    buildAllPapers(spec, dbfile)
    print("Checking papers produced and updating databases")
    confirmProcessed(spec, dbfile)


def buildNamedPapers(spec):
    if spec["numberToName"] > 0:
        print(
            'Building {} pre-named papers and {} blank papers in "{}"...'.format(
                spec["numberToName"],
                spec["numberToProduce"] - spec["numberToName"],
                paperdir,
            )
        )
    else:
        print(
            'Building {} blank papers in "{}"...'.format(
                spec["numberToProduce"], paperdir
            )
        )

    buildAllPapers(spec, dbfile, named=True)
    print("Checking papers produced and updating databases")
    confirmProcessed(spec, dbfile)
    confirmNamed(spec, dbfile)


def buildDatabaseAndPapers(blank):
    print("Reading specification")
    if not os.path.isfile(os.path.join(specdir, "verifiedSpec.toml")):
        print('Cannot find verified specFile - have you run "plom-build parse" yet?')
        exit(1)
    spec = SpecParser().spec

    if blank == "true" and spec["numberToName"] > 0:
        print(
            ">>> WARNING <<< "
            "Your spec says to produce {} named-papers, but you have run with the '--blank' option. Building unnamed papers.".format(
                spec["numberToName"]
            )
        )

    buildDatabase(spec)

    os.makedirs(paperdir, exist_ok=True)
    if blank:
        buildBlankPapers(spec)
    else:
        buildNamedPapers(spec)


parser = argparse.ArgumentParser()
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
    epilog=processClasslist.__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
group = spL.add_mutually_exclusive_group(required=True)
group.add_argument("classlist", nargs="?", help="filename in csv format")
group.add_argument(
    "--demo",
    action="store_true",
    help="Use auto-generated classlist. **DO NOT USE ON REAL SERVER**",
)

#
spB = sub.add_parser(
    "make",
    help="Make the PDFs",
    description="""
        Build papers and database from the test specification.  Based on the
        spec, some of the papers may have names printed on them from the
        classlist ("pre-named") and the remainder will be blank.""",
)
spB.add_argument(
    "-b",
    "--blank",
    action="store_true",
    help="Force building only blank papers, ignoring spec",
)


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
        # process the class list and copy into place
        processClasslist(args.classlist, args.demo)
    elif args.command == "make":
        # get building.
        buildDatabaseAndPapers(args.blank)
    else:
        # no command given so print help.
        parser.print_help()

    exit(0)


if __name__ == "__main__":
    main()
