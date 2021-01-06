#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Command line tool to start Plom servers."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import locale
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from textwrap import fill, dedent

import pkg_resources

from plom import __version__
from plom import specdir


server_instructions = """Overview of running the Plom server:

  0. Decide on a working directory for the server and cd into it.

  1. Copy the `{specdir}` directory (not just its contents) to your
     server directory.

  2. Run '%(prog)s init' - this will check that everything is in place
     and create necessary sub-directories *and* create config files for
     you to edit.

  3. Run '%(prog)s users' - This will create a template user list
     file for you to edit.  Passwords are displayed in plain text.
     Running with '--demo' option creates a (standard) demo user list,
     while '--auto N' makes an random-generated list of N users.  Edit
     as you see fit.

  4. Run '%(prog)s users <filename>' - This parses the plain-text
     user list, performs some simple sanity checks and then hashes the
     passwords to a new file.

       4a. Optionally you can now delete the file containing
           plain-text passwords.

  5. Now you can start the server with '%(prog)s launch'.

FUTURE - '%(prog)s stop' will stop the server.
""".format(
    specdir=specdir
)


class PlomServerConfigurationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def checkSpecAndDatabase():
    if os.path.isdir(specdir):
        print("Directory '{}' is present.".format(specdir))
    else:
        print(
            "Cannot find '{}' directory - you must copy this into place before running server. Cannot continue.".format(
                specdir
            )
        )
        exit(1)

    if os.path.isfile(Path(specdir) / "verifiedSpec.toml"):
        print("Test specification present.")
    else:
        print(
            "Cannot find the test specification. Have you run 'plom-build' yet?. Aborting."
        )
        exit(1)

    if os.path.isfile(Path(specdir) / "plom.db"):
        print("Database present: using existing database.")
    else:
        print("Database not yet present: it will be created on first run.")
        # TODO: or should `plom-server init` create it?")

    if os.path.isfile(Path(specdir) / "classlist.csv"):
        print("Classlist present.")
    else:
        print("Cannot find the classlist: expect it later...")


def buildRequiredDirectories():
    lst = [
        "pages",
        "pages/discardedPages",
        "pages/collidingPages",
        "pages/unknownPages",
        "pages/originalPages",
        "markedQuestions",
        "markedQuestions/plomFiles",
        "markedQuestions/commentFiles",
        "serverConfiguration",
    ]
    for dir in lst:
        os.makedirs(dir, exist_ok=True)


def buildSSLKeys():
    """Make new key and cert files if they do not yet exist."""
    key = Path("serverConfiguration") / "plom.key"
    cert = Path("serverConfiguration") / "plom-selfsigned.crt"
    if os.path.isfile(key) and os.path.isfile(cert):
        print("SSL key and certificate already exist - will not change.")
        return

    # Generate new self-signed key/cert
    sslcmd = "openssl req -x509 -sha256 -newkey rsa:2048"
    sslcmd += " -keyout {} -nodes -out {} -days 1000 -subj".format(key, cert)

    # TODO: is this the way to get two digit country code?
    tmp = locale.getdefaultlocale()[0]
    if tmp:
        twodigcc = tmp[-2:]
    else:
        twodigcc = "CA"
    sslcmd += " '/C={}/ST=./L=./CN=localhost'".format(twodigcc)
    try:
        subprocess.check_call(shlex.split(sslcmd))
    except Exception as err:
        raise PlomServerConfigurationError(
            "Something went wrong building ssl keys.\n{}\nCannot continue.".format(err)
        )


def createServerConfig():
    sd = os.path.join("serverConfiguration", "serverDetails.toml")
    if os.path.isfile(sd):
        print("Server config already exists - will not change.")
        return

    template = pkg_resources.resource_string("plom", "serverDetails.toml")
    with open(os.path.join(sd), "wb") as fh:
        fh.write(template)
    print(
        "Please update '{}' with the correct name (or IP) of your server and the port.".format(
            sd
        )
    )


def createBlankPredictions():
    pl = Path(specdir) / "predictionlist.csv"
    if os.path.isfile(pl):
        print("Predictionlist already present.")
        return
    print(
        "Predictionlist will be updated when you run ID-prediction from manager-client."
    )
    with open(pl, "w") as fh:
        fh.write("test, id\n")


def doLatexChecks():
    from plom.textools import texFragmentToPNG
    from plom.server import pageNotSubmitted

    os.makedirs("pleaseCheck", exist_ok=True)

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


def initialiseServer():
    print("Do simple existence checks on required files.")
    checkSpecAndDatabase()
    print("Build required directories")
    buildRequiredDirectories()
    print("Building self-signed ssl keys for server")
    buildSSLKeys()
    print("Copy server networking configuration template into place.")
    createServerConfig()
    print("Build blank predictionlist for identifying.")
    createBlankPredictions()
    print(
        "Do latex checks and build 'pageNotSubmitted.pdf', 'questionNotSubmitted.pdf' in case needed"
    )
    doLatexChecks()


#################


def processUsers(userFile, demo, auto):
    # if we have been passed a userFile then process it and return
    if userFile:
        print("Processing user file '{}' to 'userList.json'".format(userFile))
        if os.path.isfile(Path("serverConfiguration") / "userList.json"):
            print("WARNING - this will overwrite the existing userList.json file.")
        from plom.server import manageUserFiles

        manageUserFiles.parse_user_list(userFile)
        return

    # otherwise we have to make one for the user - check if one already there.
    if os.path.isfile(os.path.join("serverConfiguration", "userListRaw.csv")):
        print(
            "File 'userListRaw.csv' already exists in 'serverConfiguration'. Remove before continuing. Aborting."
        )
        exit(1)

    if demo:
        print(
            "Creating a demo user list at userListRaw.csv. ** DO NOT USE ON REAL SERVER **"
        )
        from plom.server import manageUserFiles

        rawfile = Path("serverConfiguration") / "userListRaw.csv"
        cl = pkg_resources.resource_string("plom", "demoUserList.csv")
        with open(rawfile, "wb") as fh:
            fh.write(cl)
        manageUserFiles.parse_user_list(rawfile)
        return

    if auto is not None:
        print("Creating an auto-generated user list at userListRaw.csv.")
        print(
            "Please edit as you see fit and then rerun 'plom-server users serverConfiguration/userListRaw.csv'"
        )
        from plom.server import manageUserFiles

        # grab required users and regular users
        lst = manageUserFiles.build_canned_users(auto)
        with open(os.path.join("serverConfiguration", "userListRaw.csv"), "w+") as fh:
            fh.write("user, password\n")
            for np in lst:
                fh.write('"{}", "{}"\n'.format(np[0], np[1]))

        return

    if not userFile:
        print(
            "Creating 'serverConfiguration/userListRaw.csv' - please edit passwords for 'manager', 'scanner', 'reviewer', and then add one or more normal users and their passwords. Note that passwords must be at least 4 characters and usernames should be at least 4 alphanumeric characters."
        )
        cl = pkg_resources.resource_string("plom", "templateUserList.csv")
        with open(os.path.join("serverConfiguration", "userListRaw.csv"), "wb") as fh:
            fh.write(cl)


#################
def checkDirectories():
    lst = [
        "pages",
        "pages/discardedPages",
        "pages/collidingPages",
        "pages/unknownPages",
        "pages/originalPages",
        "markedQuestions",
        "markedQuestions/plomFiles",
        "markedQuestions/commentFiles",
        "serverConfiguration",
    ]
    for d in lst:
        if not os.path.isdir(d):
            print(
                "Required directories are not present. Have you run 'plom-server init'?"
            )
            exit(1)


def checkServerConfigured():
    if not os.path.isfile(os.path.join("serverConfiguration", "serverDetails.toml")):
        print("Server configuration file not present. Have you run 'plom-server init'?")
        exit(1)

    if not os.path.isfile(os.path.join("serverConfiguration", "userList.json")):
        print("Processed userlist is not present. Have you run 'plom-server users'?")
        exit(1)

    if not (
        os.path.isfile(os.path.join("serverConfiguration", "plom.key"))
        and os.path.isfile(os.path.join("serverConfiguration", "plom-selfsigned.crt"))
    ):
        print("SSL keys not present. Have you run 'plom-server init'?")
        exit(1)

    if os.path.isfile(Path(specdir) / "predictionlist.csv"):
        print("Predictionlist present.")
    else:
        print(
            "Cannot find the predictionlist. Have you run 'plom-server init' yet? Aborting."
        )
        exit(1)


def prelaunchChecks():
    # check database, spec and classlist in place
    checkSpecAndDatabase()
    # check all directories built
    checkDirectories()
    # check serverConf and userlist present (also check predictionlist).
    checkServerConfigured()
    # ready to go
    return True


def launchTheServer(masterToken):
    from plom.server import theServer

    if prelaunchChecks():
        theServer.launch(masterToken)


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
#
spI = sub.add_parser("init", help="Initialise server.")
spU = sub.add_parser("users", help="Create required users.")
spR = sub.add_parser("launch", help="Launch server.")
spR.add_argument(
    "masterToken",
    nargs="?",
    help="The master token is a 32 hex-digit string used to encrypt tokens in database. If you do not supply one then the server will create one. You should record the token somewhere (and reuse it at next server-start) if you want to be able to hot-restart the server (ie - restart the server without requiring users to log-off and log-in again).",
)
#
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
    help="Construct an auto-generated user list of N users.",
)


def main():
    args = parser.parse_args()

    if args.command == "init":
        initialiseServer()
    elif args.command == "users":
        # process the class list and copy into place
        processUsers(args.userlist, args.demo, args.auto)
    elif args.command == "launch":
        launchTheServer(args.masterToken)
    else:
        parser.print_help()

    exit(0)


if __name__ == "__main__":
    main()
