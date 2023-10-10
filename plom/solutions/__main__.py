#!/usr/bin/env python3

# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2023 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for pushing/pulling solution page images to/from a server.

The plom-solutions command allows you to
  * extract solutions from pdfs
  * upload solution images
  * download a solution image
  * check which questions/versions have solutions
  * reassemble solutions for individual students.

For further information on extracting & uploading solutions, and
on returning solutions to students please run
`plom-solutions info`
"""

__copyright__ = "Copyright (C) 2021-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import sys

from stdiomask import getpass

from plom import __version__
from plom import Default_Port
from plom.solutions import clear_manager_login
from plom.solutions import deleteSolutionImage, putSolutionImage
from plom.solutions import getSolutionImage
from plom.solutions import checkStatus
from plom.solutions import putExtractedSolutionImages
from plom.solutions import extractSolutionImages
from plom.plom_exceptions import PlomNoSolutionException


longerHelp = """
## Extracting and uploading solutions
  * Using `plom-solution extract` you can auto-extract and combine
    solution page images from pdfs of your test solutions.
  * Plom will assume that you create solution PDFs for your test
    that, broadly speaking, mimic the structure of your question PDFs.
    That is
      - you have one solution file for each version of your test
      - each solution file has the same structure. For example,
        your solution to Q3 is on pages 4 and 5 for each version
        rather than (say) p3,4 in V1 and p4,5 in V2.
      - the solution files are sitting in the same 'sourceVersions'
        directory as your sourceX.pdf test pdfs. They should be
        named 'solutionsX.pdf' where X is the version number.
  * If your solution pdfs have identical structure to your test-pdfs,
    ie solutions for Q3 are on exactly the pages you specified in
    your test spec for Q3, then you can simply run
        `plom-solutions extract --upload`
    or perhaps
        `plom-solutions extract --upload --server ...`
  * This will then take pages from your `solutionsX.pdf` files and
    combine them into a solution png file for each question/version
    and place the results in the `solutionImages` directory
  * Those images will then automatically be uploaded to the Plom server.
  * If the structure of your solution pdfs is different from your test
    pdfs, then you can construct a simple solutionSpec.toml file, such as:
    "
        numberOfVersions = 2
        numberOfPages = 6
        numberOfQuestions = 3
        [solution.1]
        pages = [3]
        [solution.2]
        pages = [4]
        [solution.3]
        pages = [5]
    "
    You can then extract and upload your solutions using this spec via
       `plom-solutions extract --upload mySolutionSpec.toml`

## Assembling solutions for individual students
  * Once marking is finished and you have reassembled papers for students
    You can also assemble solutions for individual students.
  * The `plom-finish solutions` command will build a solution PDF for
    each student based on the particular version of each question on
    the student's paper.
  * To auto-build a return webpage that includes solutions for students
    run `plom-finish webpage --solutions`
    The solution webpage will then have a "get solutions" button which
    provides those personalised solutions.
"""


def print_more_help():
    print(longerHelp)


def solutionStatus(server, password):
    solutionList = checkStatus(msgr=(server, password))
    # will be a list of triples [q,v,md5sum] or [q,v,""]
    for qvm in solutionList:
        if qvm[2] == "":
            print("q {} v {} = no solution".format(qvm[0], qvm[1]))
        else:
            print("q {} v {} = solution with md5sum {}".format(qvm[0], qvm[1], qvm[2]))


def extractSolutions(solutionSpec=None, upload=False, *, msgr):
    if upload:
        print("Uploading extracted solution images extracted")
        putExtractedSolutionImages(msgr=msgr)
        return

    if extractSolutionImages(solutionSpec, msgr=msgr):
        print("Solution images extracted")
    else:
        print("Could not extract solution images - see messages above.")


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser(
        "info",
        help="Print more information on extracting, uploading and returning solutions.",
        description="Print more information on extracting, uploading and returning solutions.",
    )
    spU = sub.add_parser(
        "upload",
        help="Upload solution image to the server",
        description="Upload solution image to the server.",
    )
    spG = sub.add_parser(
        "get",
        help="Get solution image from the server",
        description="Get solution image from the server.",
    )
    spD = sub.add_parser(
        "delete",
        help="Delete solution image from the server",
        description="Delete solution image from the server.",
    )
    spS = sub.add_parser(
        "status",
        help="Get uploaded solution status",
        description="Get list of which question/versions have solution-images uploaded",
    )
    spE = sub.add_parser(
        "extract",
        help="Extract solution images from solution pdfs",
        description="""
            Extract solutions images from solution PDF file.  By default
            it assumes the same structure as the blank papers, or you
            can pass in solution spec file.""",
    )
    spC = sub.add_parser(
        "clear",
        help='Clear "manager" login',
        description='Clear "manager" login after a crash or other expected event.',
    )

    spU.add_argument(
        "q",
        action="store",
        help="The question to upload to",
    )
    spU.add_argument(
        "v",
        action="store",
        help="The version to upload to",
    )
    spU.add_argument("image", help="The image of the solution.")

    spG.add_argument(
        "q",
        action="store",
        help="The question to get",
    )
    spG.add_argument(
        "v",
        action="store",
        help="The version to get",
    )
    spD.add_argument(
        "q",
        action="store",
        help="The question to delete",
    )
    spD.add_argument(
        "v",
        action="store",
        help="The version to delete",
    )

    spE.add_argument(
        "solutionSpec",
        nargs="?",
        help="""
           A simple spec file that describes the solutions.  If none given,
           then one will be auto-generated from the test spec assuming the
           same structure and saved as solutionSpec.toml.""",
    )
    spE.add_argument(
        "-u",
        "--upload",
        action="store_true",
        help="Do not extract, instead upload already extracted solution images to server.",
    )

    for x in (spU, spG, spD, spS, spE, spC):
        x.add_argument(
            "-s",
            "--server",
            metavar="SERVER[:PORT]",
            action="store",
            help=f"""
                Which server to contact, port defaults to {Default_Port}.
                Also checks the environment variable PLOM_SERVER if omitted.
            """,
        )
        x.add_argument(
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

    if args.command == "upload":
        ok, msg = putSolutionImage(
            args.q, args.v, args.image, msgr=(args.server, args.password)
        )
        if ok:
            print(f"Success: {msg}")
        else:
            print(f"Failure: {msg}")
            sys.exit(1)

    elif args.command == "get":
        img = getSolutionImage(args.q, args.v, msgr=(args.server, args.password))
        with open("solution.{}.{}.png".format(args.q, args.v), "wb") as fh:
            fh.write(img)

    elif args.command == "delete":
        try:
            deleteSolutionImage(args.q, args.v, msgr=(args.server, args.password))
            print(
                f"Successfully removed solution to question {args.q} version {args.v}"
            )
        except PlomNoSolutionException as e:
            print(e)
            sys.exit(1)

    elif args.command == "status":
        solutionStatus(args.server, args.password)
    elif args.command == "extract":
        extractSolutions(
            args.solutionSpec, args.upload, msgr=(args.server, args.password)
        )
    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    elif args.command == "info":
        print_more_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
