#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023, 2025 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2023 Julian Lapenna

"""Plom tools for pushing and manipulating bundles from the command line.

See help for each subcommand or consult online documentation for an
overview of the steps in setting up a server.

Most subcommands communicate with a server, which can be specified
on the command line or by setting environment variables PLOM_SERVER
PLOM_USERNAME and PLOM_PASSWORD.
"""

__copyright__ = "Copyright (C) 2020-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path

from stdiomask import getpass

from plom.scan import __version__
from plom import Default_Port
from plom.cli import list_bundles, with_messenger
from plom.scan.question_list_utils import _parse_questions

# from plom.cli import clear_login


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

    spU = sub.add_parser(
        "upload-bundle",
        help="Upload PDF file",
        description="Upload a bundle of page images in a PDF file.",
    )
    spU.add_argument("pdf", help="a PDF file.")
    spS = sub.add_parser(
        "list-bundles",
        help="List the scanned bundles on the server",
    )
    spC = sub.add_parser(
        "clear",
        help='Clear "scanner" login',
        description='Clear "scanner" login after a crash or other expected event.',
    )
    sp_map = sub.add_parser(
        "map",
        help="Assign pages of a bundle to particular questions.",
        description="""
            Assign pages of a bundle to particular question(s),
            ignoring QR-codes etc.
        """,
    )
    # TODO: might be convenient to work with stub/pdf name as well
    sp_map.add_argument("bundle_id", help="Which bundle")
    sp_map.add_argument("bundle_page", help="Which page of the bundle")
    sp_map.add_argument(
        "--papernum",
        "-t",
        metavar="T",
        type=int,
        help="""
            Which paper number to upload to.
            It must exist; you must create it first with appropriate
            versions.
            TODO: argparse has this as optional but no default setting
            for this yet: maybe it should assign to the next available
            paper number or something like that?
        """,
    )
    sp_map.add_argument(
        "-q",
        "--question",
        metavar="N",
        help="""
            Which question(s) are answered in file.
            You can pass a single integer, or a list like `-q [1,2,3]`
            which updates each page to questions 1, 2 and 3.
            You can also pass the special string `-q all` which uploads
            each page to all questions (this is also the default).
            If you need to specify questions per page, you can pass a list
            of lists: each list gives the questions for each page.
            For example, `-q [[1],[2],[2],[2],[3]]` would upload page 1 to
            question 1, pages 2-4 to question 2 and page 5 to question 3.
            A common case is `-q [[1],[2],[3]]` to upload one page per
            question.
            An empty list will "discard" that particular page.
        """,
    )

    for x in (spU, spS, spC, sp_map):
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
            "-u",
            "--username",
            type=str,
            help="""
                Also checks the
                environment variable PLOM_USERNAME.
            """,
        )
        x.add_argument(
            "-w",
            "--password",
            type=str,
            help="""
                Also checks the
                environment variable PLOM_SCAN_PASSWORD.
            """,
        )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "server"):
        args.server = args.server or os.environ.get("PLOM_SERVER")

    if hasattr(args, "username"):
        args.username = args.username or os.environ.get("PLOM_USERNAME")

    if hasattr(args, "password"):
        args.password = args.password or os.environ.get("PLOM_PASSWORD")

    if hasattr(args, "username") and not args.username:
        args.username = input("username: ")
    if hasattr(args, "password") and not args.password:
        args.password = getpass("password: ")

    if args.command == "upload-bundle":

        @with_messenger
        def upload(pdf, *, msgr):
            r = msgr.new_server_upload_bundle(pdf)
            print(r)

        print("TODO")
        upload(Path(args.pdf), msgr=(args.server, args.username, args.password))
    elif args.command == "list-bundles":
        list_bundles(msgr=(args.server, args.username, args.password))
    elif args.command == "map":

        @with_messenger
        def todo(bundle_id, page, *, papernum, questions, msgr):
            print((bundle_id, papernum, questions))
            r = msgr.new_server_bundle_map_page(bundle_id, page, papernum, questions)
            print(r)

        # num_pages = 7  # TODO:
        # N = 4  # TODO:
        # questions = canonicalize_page_question_map(
        #     args.question, pages=num_pages, numquestions=N
        # )
        questions = _parse_questions(args.question)

        todo(
            args.bundle_id,
            args.bundle_page,
            papernum=args.papernum,
            questions=questions,
            msgr=(args.server, args.username, args.password),
        )

    elif args.command == "clear":
        print("TODO: do we need this on new Plom?")
        # clear_login(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
