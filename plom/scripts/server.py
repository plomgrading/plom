#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Morgan Arnold

"""Command line tool to start Plom servers."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import shutil
from pathlib import Path
import sys
from textwrap import fill, dedent

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import plom
from plom import __version__
from plom import Default_Port
from plom.server import specdir, confdir
from plom.server import build_server_directories, check_server_directories
from plom.server import create_server_config, create_blank_predictions
from plom.server import parse_user_list, build_canned_users
from plom.server import build_self_signed_SSL_keys


server_instructions = """Overview of running the Plom server:

  0. Make a new directory and change into it.

  1. Run '%(prog)s init' - creates sub-directories and config files.

  2. Run '%(prog)s users' - creates a template user list for you to edit.

  3. Run '%(prog)s users <filename>' - parses user list for server.

       3a. Optionally you can delete the plain-text passwords.

  4. Add a specfile to '{specdir}': 'plom-build' can do this..

  5. Now you can start the server with '%(prog)s launch'.
""".format(
    specdir=specdir
)


class PlomServerConfigurationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def checkSpecAndDatabase():
    if specdir.exists():
        print("Directory '{}' is present.".format(specdir))
    else:
        print(
            "Cannot find '{}' directory - have you run 'plom-server init' yet?".format(
                specdir
            )
        )
        exit(1)

    if (specdir / "verifiedSpec.toml").exists():
        print("Test specification present.")
    else:
        print(
            "Cannot find the test specification. Have you run 'plom-build' yet?. Aborting."
        )
        exit(1)

    if (specdir / "plom.db").exists():
        print("Database present: using existing database.")
    else:
        print("Database not yet present: it will be created on first run.")
        # TODO: or should `plom-server init` create it?")

    if (specdir / "classlist.csv").exists():
        print("Classlist present.")
    else:
        print("Cannot find the classlist: expect it later...")


def doLatexChecks():
    from plom.textools import texFragmentToPNG
    from plom.server import pageNotSubmitted

    os.makedirs("pleaseCheck", exist_ok=True)

    # TODO: big ol' GETCWD here: we're trying to get rid of those
    # check build of fragment
    cdir = os.getcwd()
    keepfiles = ("checkThing.png", "pns.0.0.0.png")
    ct = os.path.join(cdir, "pleaseCheck", keepfiles[0])
    pns = os.path.join(cdir, specdir, "pageNotSubmitted.pdf")
    qns = os.path.join(cdir, specdir, "questionNotSubmitted.pdf")

    fragment = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ worked okay for plom."

    if not texFragmentToPNG(fragment, ct):
        raise PlomServerConfigurationError(
            "Error latex'ing fragment. Please check your latex distribution."
        )

    # build template pageNotSubmitted.pdf just in case needed
    if not pageNotSubmitted.build_not_submitted_page(pns):
        raise PlomServerConfigurationError(
            "Error building 'pageNotSubmitted.pdf' template page. Please check your latex distribution."
        )
    # build template pageNotSubmitted.pdf just in case needed
    if not pageNotSubmitted.build_not_submitted_question(qns):
        raise PlomServerConfigurationError(
            "Error building 'questionNotSubmitted.pdf' template page. Please check your latex distribution."
        )

    # Try building a replacement for missing page.
    if not pageNotSubmitted.build_test_page_substitute(0, 0, 0):
        raise PlomServerConfigurationError(
            "Error building replacement for missing test page."
        )
    # Try building a replacement for missing page.
    if not pageNotSubmitted.build_homework_question_substitute(0, 0):
        raise PlomServerConfigurationError(
            "Error building replacement for missing homework question."
        )

    shutil.move(keepfiles[1], os.path.join("pleaseCheck", keepfiles[1]))
    print(
        fill(
            dedent(
                """
                Simple latex checks done.  If you feel the need, then please
                examine '{}' and '{}' in the directory 'pleaseCheck'.  The
                first should be a short latex'd fragment with some mathematics
                and text, while the second should be a mostly blank page with
                'page not submitted' stamped across it.  It is safe delete
                both files and the directory.
                """.format(
                    *keepfiles
                )
            )
        )
    )


def initialiseServer(port):
    print("Build required directories")
    build_server_directories()
    print("Building self-signed SSL key for server")
    try:
        build_self_signed_SSL_keys()
    except FileExistsError as err:
        print(f"Skipped SSL keygen - {err}")

    print("Copy server networking configuration template into place.")
    try:
        create_server_config(port=port)
    except FileExistsError as err:
        print(f"Skipping server config - {err}")
    else:
        print(
            "You may want to update '{}' with the correct name (or IP) and "
            "port of your server.".format(confdir / "serverDetails.toml")
        )

    print("Build blank predictionlist for identifying.")
    try:
        create_blank_predictions()
    except FileExistsError as err:
        print(f"Skipping prediction list - {err}")

    print(
        "Do latex checks and build 'pageNotSubmitted.pdf', 'questionNotSubmitted.pdf' in case needed"
    )
    doLatexChecks()


#################


def processUsers(userFile, demo, auto, auto_num):
    """Deal with processing and/or creation of username lists.

    Behaviour different depending on the args.

    args:
        userFile (str/pathlib.Path): a filename of usernames/passwords
            for the server.
        demo (bool): make canned demo with known usernames/passwords.
        auto (bool): autogenerate usernames and passwords.
        auto_num (bool): autogenerate usernames like "user03" and pwds.

    return:
        None
    """
    confdir.mkdir(exist_ok=True)
    userlist = confdir / "userList.json"
    # if we have been passed a userFile then process it and return
    if userFile:
        print("Processing user file '{}' to {}".format(userFile, userlist))
        if userlist.exists():
            print("WARNING - overwriting existing {} file.".format(userlist))
        parse_user_list(userFile)
        return

    rawfile = confdir / "userListRaw.csv"
    # otherwise we have to make one for the user - check if one already there.
    if rawfile.exists():
        raise FileExistsError(
            "File {} already exists.  Remove and try again.".format(rawfile)
        )

    if demo:
        print(
            "Creating a demo user list at {}. "
            "** DO NOT USE ON REAL SERVER **".format(rawfile)
        )
        cl = resources.read_binary(plom, "demoUserList.csv")
        with open(rawfile, "wb") as fh:
            fh.write(cl)
        parse_user_list(rawfile)
        return

    if auto or auto_num:
        if auto:
            N = auto
            numbered = False
        if auto_num:
            N = auto_num
            numbered = True
        del auto
        del auto_num
        print(
            "Creating an auto-generated {0} user list at '{1}'\n"
            "Please edit as you see fit and then rerun 'plom-server users {1}'".format(
                "numbered" if numbered else "named",
                rawfile,
            )
        )
        # grab required users and regular users
        lst = build_canned_users(N, numbered)
        with open(rawfile, "w+") as fh:
            fh.write("user, password\n")
            for np in lst:
                fh.write('"{}", "{}"\n'.format(np[0], np[1]))
        return

    if not userFile:
        print(
            "Creating '{}' - please edit passwords for 'manager', 'scanner', 'reviewer', and then add one or more normal users and their passwords. Note that passwords must be at least 4 characters.".format(
                rawfile
            )
        )
        cl = resources.read_binary(plom, "templateUserList.csv")
        with open(rawfile, "wb") as fh:
            fh.write(cl)


def checkServerConfigured():
    if not (confdir / "serverDetails.toml").exists():
        print("Server configuration file not present. Have you run 'plom-server init'?")
        exit(1)

    if not (confdir / "userList.json").exists():
        print("Processed userlist is not present. Have you run 'plom-server users'?")
        exit(1)

    if not (
        (confdir / "plom.key").exists() and (confdir / "plom-selfsigned.crt").exists()
    ):
        print("SSL keys not present. Have you run 'plom-server init'?")
        exit(1)

    if (specdir / "predictionlist.csv").exists():
        print("Predictionlist present.")
    else:
        print(
            "Cannot find the predictionlist. Have you run 'plom-server init' yet? Aborting."
        )
        exit(1)


def launchTheServer(masterToken):
    from plom.server import theServer

    check_server_directories()
    # check database, spec and classlist in place
    checkSpecAndDatabase()
    # check serverConf and userlist present (also check predictionlist).
    checkServerConfigured()

    theServer.launch(masterToken)


def check_positive(arg):
    if int(arg) < 0:
        raise ValueError
    return int(arg)


#################

parser = argparse.ArgumentParser(
    epilog="Use '%(prog)s <subcommand> -h' for detailed help.\n\n"
    + server_instructions,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(
    dest="command", description="Perform various server-related tasks."
)

spI = sub.add_parser(
    "init",
    help="Initialise server",
    description="""
      Initializes the current working directory in preparation for
      starting a Plom server.  Creates sub-directories and config files.
    """,
)
spI.add_argument(
    "--port",
    type=int,
    help=f"Use alternative port (defaults to {Default_Port} if omitted)",
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
    "masterToken",
    nargs="?",
    help="""A 32 hex-digit string used to encrypt tokens in the database.
        If you do not supply one then the server will create one.
        If you record the token somewhere you can hot-restart the server
        (i.e., restart the server without requiring users to log-off and
        log-in again).""",
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
    help="Use demo auto-generated userlist and passwords. **DO NOT DO THIS ON REAL SERVER**",
)
grp.add_argument(
    "--auto",
    type=int,
    metavar="N",
    help="Auto-generate a random user list of N users with real-ish usernames.",
)
grp.add_argument(
    "--auto-numbered",
    type=check_positive,
    metavar="N",
    help='Auto-generate a random user list of "user17"-like usernames.',
)


def main():
    args = parser.parse_args()

    if args.command == "init":
        initialiseServer(args.port)
    elif args.command == "users":
        processUsers(args.userlist, args.demo, args.auto, args.auto_numbered)
    elif args.command == "launch":
        launchTheServer(args.masterToken)
    else:
        parser.print_help()

    exit(0)


if __name__ == "__main__":
    main()
