#!/usr/bin/env python3

# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for pushing solution page image up to server"""
__copyright__ = "Copyright (C) 2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os

from plom import __version__


def uploadSolutionImage(server, password, question, version, imageName):
    from plom.solutions import putSolutionImage

    rv = putSolutionImage.putSolutionImage(
        question, version, imageName, server, password
    )
    if rv[0]:
        print(f"Success - {rv[1]}")
    else:
        print(f"Failure - {rv[1]}")


def deleteSolutionImage(server, password, question, version):
    from plom.solutions import deleteSolutionImage

    if deleteSolutionImage.deleteSolutionImage(question, version, server, password):
        print(
            "Successfully removed solution to question {} version {}".format(
                question, version
            )
        )
    else:
        print(
            "There was no solution to question {} version {} to remove".format(
                question, version
            )
        )


def getSolutionImage(server, password, question, version):
    from plom.solutions import getSolutionImage

    img = getSolutionImage.getSolutionImage(question, version, server, password)
    if img is not None:
        with open("solution.{}.{}.png".format(question, version), "wb") as fh:
            fh.write(img)


def solutionStatus(server, password):
    from plom.solutions import checkSolutionStatus

    solutionList = checkSolutionStatus.checkStatus(server, password)
    # will be a list of triples [q,v,md5sum] or [q,v,""]
    for qvm in solutionList:
        if qvm[2] == "":
            print("q {} v {} = no solution".format(qvm[0], qvm[1]))
        else:
            print("q {} v {} = solution with md5sum {}".format(qvm[0], qvm[1], qvm[2]))


def extractSolutions(server, password, solutionSpec=None, upload=False):
    if upload:
        from plom.solutions.putSolutionImage import putExtractedSolutionImages

        print("Uploading extracted solution images extracted")
        putExtractedSolutionImages(server, password)
        return

    from plom.solutions.extractSolutions import extractSolutionImages

    if extractSolutionImages(server, password, solutionSpec):
        print("Solution images extracted")
    else:
        print("Could not extract solution images - see messages above.")


def clearLogin(server, password):
    from plom.solutions import clearManagerLogin

    clearManagerLogin.clearLogin(server, password)


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command")

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
    help="Delete solution image from the scanner",
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
    description="Extract solutions images from solution pdfs - assumes that solution pdf has the same structure as the test pdf.",
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
    help="A simple spec file that describes the solutions. If none given, then one will be auto-generated from the test spec assuming the same structure and saved as solutionSpec.toml.",
)
spE.add_argument(
    "-u",
    "--upload",
    action="store_true",
    help="Do not extract, instead upload already extracted solution images to server.",
)

for x in (spU, spG, spD, spS, spE, spC):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_SCAN_PASSWORD"]
        except KeyError:
            pass

    if args.command == "upload":
        uploadSolutionImage(args.server, args.password, args.q, args.v, args.image)
    if args.command == "get":
        getSolutionImage(args.server, args.password, args.q, args.v)
    if args.command == "delete":
        deleteSolutionImage(args.server, args.password, args.q, args.v)
    elif args.command == "status":
        solutionStatus(args.server, args.password)
    elif args.command == "extract":
        extractSolutions(args.server, args.password, args.solutionSpec, args.upload)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
