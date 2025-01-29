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

from plom import Default_Port, __version__
from plom.cli import (
    bundle_map_page,
    get_reassembled,
    id_paper,
    un_id_paper,
    list_bundles,
    start_messenger,
    upload_bundle,
)

# from plom.cli import clear_login


def _get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(dest="command")

    def _add_server_args(x):
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
                environment variable PLOM_PASSWORD.
            """,
        )

    s = sub.add_parser(
        "get-reassembled",
        help="Get a reassembled paper.",
        description="""
            Download a reassembled paper as a PDF file from the server.
            Will fail if the paper is not reassembled yet.
        """,
    )
    s.add_argument("papernum", type=int)
    _add_server_args(s)

    s = sub.add_parser(
        "upload-bundle",
        help="Upload PDF file",
        description="Upload a bundle of page images in a PDF file.",
    )
    s.add_argument("pdf", help="a PDF file.")
    _add_server_args(s)

    s = sub.add_parser(
        "list-bundles",
        help="List the scanned bundles on the server",
    )
    _add_server_args(s)

    s = sub.add_parser(
        "push-bundle",
        help="Declare that a bundle is ready for marking",
        description="""
            A bundle that is ready to be marked (e.g., no unknown pages etc)
            is ready for marking.  This command moves its pages from the staging
            area and makes them available for marking.

            Use the `list-bundles` command to check on the status of your bundle.
        """,
    )
    _add_server_args(s)
    s.add_argument("bundle_id", type=int)

    s = sub.add_parser(
        "delete-bundle",
        help="Delete a bundle from the staging area, NOT IMPLEMENTED YET",
    )
    _add_server_args(s)
    s.add_argument("bundle_id", type=int)

    s = sub.add_parser(
        "wait-bundle",
        help="Wait for a bundle to finish processing, NOT IMPLEMENTED YET",
    )
    _add_server_args(s)
    s.add_argument("bundle_id", type=int)

    s = sub.add_parser(
        "id-paper",
        help="Identify a paper by associating it with a particular student",
        description="""
            Identify a paper by associating it with a particular student id
            (and name).  The id must be unique and not in use.  The name is
            essentially arbitrary (as lots of people have the same name).
            This tool doesn't care about mundane things like classlists.
            Its your responsibility to send reasonable data that has meaning
            to you.
        """,
    )
    _add_server_args(s)
    s.add_argument("papernum", type=int, help="Which paper number to identify")
    s.add_argument("--sid", type=str)
    s.add_argument("--name", type=str)

    s = sub.add_parser(
        "un-id-paper",
        help="Unidentify a paper, removing the association with a student",
    )
    _add_server_args(s)
    s.add_argument("papernum", type=int, help="Which paper number to identify")

    s = sub.add_parser(
        "clear",
        help='Clear "scanner" login',
        description='Clear "scanner" login after a crash or other expected event.',
    )
    _add_server_args(s)

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
            Which paper number to attach the page to.
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
            Which question(s) are answered on the page.
            You can pass a single integer, or a list like `-q [1,2,3]`
            which attaches the page to questions 1, 2 and 3.
            You can also pass the special string `-q all` which attaches
            the page to all questions (this is also the default).
            An empty list will "discard" that particular page.
            TODO: discard, dnm and all are currently "in-flux".
        """,
    )
    _add_server_args(sp_map)
    return parser


def main():
    """The plom-cli command line tool."""
    parser = _get_parser()
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
        r = upload_bundle(
            Path(args.pdf), msgr=(args.server, args.username, args.password)
        )
        print(r)
    elif args.command == "list-bundles":
        list_bundles(msgr=(args.server, args.username, args.password))
    elif args.command == "push-bundle":
        msgr = start_messenger(args.server, args.username, args.password)
        try:
            r = msgr.new_server_push_bundle(args.bundle_id)
            print(r)
        finally:
            msgr.closeUser()
            msgr.stop()

    elif args.command == "map":
        bundle_map_page(
            args.bundle_id,
            args.bundle_page,
            papernum=args.papernum,
            questions=args.question,
            msgr=(args.server, args.username, args.password),
        )

    elif args.command == "id-paper":
        id_paper(
            args.papernum,
            args.sid,
            args.name,
            msgr=(args.server, args.username, args.password),
        )

    elif args.command == "un-id-paper":
        un_id_paper(args.papernum, msgr=(args.server, args.username, args.password))

    elif args.command == "get-reassembled":
        r = get_reassembled(
            args.papernum, msgr=(args.server, args.username, args.password)
        )
        print(
            f"wrote reassembled paper number {args.papernum} to "
            f'file {r["filename"]} [{r["content-length"]} bytes]'
        )
    elif args.command == "clear":
        print("TODO: do we need this on new Plom?")
        # clear_login(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
