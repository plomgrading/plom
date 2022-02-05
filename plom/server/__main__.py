#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Morgan Arnold
# Copyright (C) 2021 Nicholas J H Lai

"""Command line tool to start Plom servers."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import csv
from pathlib import Path

from plom import __version__
from plom import Default_Port
from plom.server import specdir, confdir
from plom.server import theServer
from plom.server.prepare import initialise_server
from plom.server import (
    build_canned_users,
    check_server_directories,
    check_server_fully_configured,
)
from plom.server.manageUserFiles import (
    parse_and_save_user_list,
    write_template_csv_user_list,
)


server_instructions = f"""Overview of running the Plom server:

  0. Make a new directory and change into it.

  1. Run '%(prog)s init' - creates sub-directories and config files.

  2. Run '%(prog)s users' - creates a template user list for you to edit.

  3. Run '%(prog)s users <filename>' - parses user list for server.

       3a. Optionally you can delete the plain-text passwords.

  4. Add a specfile to '{specdir}': 'plom-create' can do this..

  5. Now you can start the server with '%(prog)s launch'.
"""


def processUsers(userFile, demo, auto, numbered):
    """Deal with processing and/or creation of username lists.

    Behaviour different depending on the args.

    args:
        userFile (str/pathlib.Path): a filename of usernames/passwords
            for the server.
        demo (bool): make canned demo with known usernames/passwords.
        auto (int or None): number of autogenerate usernames and passwords.
        numbered (bool): autogenerate usernames like "user03" and pwds.

    return:
        None
    """
    userlist = confdir / "userList.json"
    # if we have been passed a userFile then process it and return
    if userFile:
        print("Processing user file '{}' to {}".format(userFile, userlist))
        if userlist.exists():
            print("WARNING - overwriting existing {} file.".format(userlist))
        parse_and_save_user_list(userFile)
        return

    rawfile = Path("userListRaw.csv")
    # otherwise we have to make one for the user
    if rawfile.exists():
        raise FileExistsError(f"File {rawfile} already exists: remove and try again.")

    if demo:
        print(
            f"Creating a demo user list at {rawfile}. ** DO NOT USE ON REAL SERVER **"
        )
        write_template_csv_user_list(rawfile)
        parse_and_save_user_list(rawfile)
        return

    if auto is not None:
        print(
            "Creating an auto-generated {0} user list at '{1}'\n"
            "Please edit as you see fit and then rerun 'plom-server users {1}'".format(
                "numbered" if numbered else "named",
                rawfile,
            )
        )
        # grab required users and regular users
        lst = build_canned_users(auto, numbered)
        with open(rawfile, "w") as fh:
            writer = csv.writer(fh, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(["user", "password"])
            for row in lst:
                writer.writerow(row)
        return

    if not userFile:
        print(
            "Creating '{}' - please edit passwords for 'manager', 'scanner', 'reviewer', and then add one or more normal users and their passwords. Note that passwords must be at least 4 characters.".format(
                rawfile
            )
        )
        write_template_csv_user_list(rawfile)


def check_non_negative(arg):
    if int(arg) < 0:
        raise ValueError
    return int(arg)


def get_parser():
    parser = argparse.ArgumentParser(
        epilog="Use '%(prog)s <subcommand> -h' for detailed help.\n\n"
        + server_instructions,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    sub = parser.add_subparsers(
        dest="command", description="Perform various server-related tasks."
    )

    spI = sub.add_parser(
        "init",
        help="Initialise server",
        description="""
          Initialises a directory in preparation for starting a Plom server.
          Creates sub-directories, config files, and various other things.
        """,
    )
    spI.add_argument(
        "dir",
        nargs="?",
        help="The directory to use. If omitted, use the current directory.",
    )
    spI.add_argument(
        "--port",
        type=int,
        help=f"Use alternative port (defaults to {Default_Port} if omitted)",
    )
    spI.add_argument(
        "--server-name",
        metavar="NAME",
        type=str,
        help="""
            The server name such as "plom.example.com" or an IP address.
            Defaults to something like "localhost" if omitted, but
            you may, e.g., want to match your SSL certificate.
        """,
    )
    spI.add_argument(
        "--no-self-signed",
        action="store_false",
        dest="selfsigned",
        help="""
            Do not build self-signed SSL cert and key.  You will need to
            provide plom-custom.key and plom-custom.cert in this case.
        """,
    )

    spU = sub.add_parser(
        "users",
        help="Create user accounts",
        description="""
          Manipulate users accounts.  With no arguments, produce a template
          file for you to edit, with passwords displayed in plain text.
          Given a filename, parses a plain-text user list, performs some
          simple sanity checks and then hashes the passwords a file for the
          server.
        """,
    )
    spR = sub.add_parser(
        "launch", help="Start the server", description="Start the Plom server."
    )
    spR.add_argument(
        "dir",
        nargs="?",
        help="""The directory containing the filespace to be used by this server.
            If omitted the current directory will be used.""",
    )
    spR.add_argument(
        "--mastertoken",
        metavar="HEX",
        help="""A 32 hex-digit string used to encrypt tokens in the database.
            If you do not supply one then the server will create one.
            If you record the token somewhere you can hot-restart the server
            (i.e., restart the server without requiring users to log-off and
            log-in again).""",
    )
    spR.add_argument(
        "--logfile",
        help="""A filename to save the logs.  If its a bare filename it will
            be relative to DIR above, or you can specify a path relative to
            the current working directory.""",
    )
    spR.add_argument(
        "--no-logconsole",
        action="store_false",
        dest="logconsole",
        help="""By default the server echos the logs to stderr.  This disables
            that.  You can still see the logs in the logfile.""",
    )

    spU.add_argument(
        "userlist",
        nargs="?",
        help="Process the given userlist file OR if none given then produce a template.",
    )

    grp = spU.add_mutually_exclusive_group()
    grp.add_argument(
        "--demo",
        action="store_true",
        help="""
            Use fixed prepopulated demo userlist and passwords.
            **DO NOT USE THIS ON REAL SERVER**
        """,
    )
    grp.add_argument(
        "--auto",
        type=check_non_negative,
        metavar="N",
        help="Auto-generate a random user list of N users with real-ish usernames.",
    )

    spU.add_argument(
        "--numbered",
        action="store_true",
        help='Use numbered usernames, e.g. "user17", for the autogeneration.',
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.command == "init":
        initialise_server(
            args.dir,
            port=args.port,
            name=args.server_name,
            make_selfsigned_keys=args.selfsigned,
        )
    elif args.command == "users":
        processUsers(args.userlist, args.demo, args.auto, args.numbered)
    elif args.command == "launch":
        if args.dir is None:
            args.dir = Path(".")
        # TODO: probably these checks are unnecessary and done by the server
        check_server_directories(args.dir)
        check_server_fully_configured(args.dir)
        theServer.launch(
            args.dir,
            master_token=args.mastertoken,
            logfile=args.logfile,
            logconsole=args.logconsole,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
