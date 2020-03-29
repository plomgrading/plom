#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import locale
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from textwrap import fill, dedent

# import tools for dealing with resource files
import pkg_resources

from plom import SpecVerifier, SpecParser

#################


class PlomServerConfigurationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


#################
def processClasslist(fname, demo):
    os.makedirs("specAndDatabase", exist_ok=True)
    # check if classlist.csv is in place - if so abort.
    if os.path.isfile(os.path.join("specAndDatabase", "classlist.csv")):
        print(
            "Classlist file already present in 'specAndDatabase' directory. Aborting."
        )
        exit(1)

    if demo:
        print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
        cl = pkg_resources.resource_string("plom", "demoClassList.csv")
        with open(os.path.join("specAndDatabase", "classlist.csv"), "wb") as fh:
            fh.write(cl)
        return

    from plom.produce import buildClasslist

    # check if a filename given
    if fname is None:
        buildClasslist.acceptedFormats()
        print("Please provide a classlist file.")
        exit(1)
    # grab the file, process it and copy it into place.

    if os.path.isfile(fname):
        buildClasslist.getClassList(fname)
    else:
        print('Cannot find classlist file "{}"'.format(fname))
        exit(1)


def checkSpecAndDatabase():
    if os.path.isdir("specAndDatabase"):
        print("Directory 'specAndDatabase' is present.")
    else:
        print(
            "Cannot find 'specAndDatabase' directory - you must copy this into place before running server. Cannot continue."
        )
        exit(1)

    if os.path.isfile(os.path.join("specAndDatabase", "verifiedSpec.toml")):
        print("Test specification present.")
    else:
        print(
            "Cannot find the test specification. Have you run 'plom-build' yet?. Aborting."
        )
        exit(1)

    if os.path.isfile(os.path.join("specAndDatabase", "plom.db")):
        print("Database present.")
    else:
        print("Cannot find the database. Have you run 'plom-build' yet? Aborting.")
        exit(1)

    if os.path.isfile(os.path.join("specAndDatabase", "classlist.csv")):
        print("Classlist present.")
    else:
        print(
            "Cannot find the classlist. Aborting.\nYou do not have to return to 'plom-build'. To process a classlist please run 'plom-server class <filename>'"
        )
        exit(1)


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
    # check if key/crt already exist;
    if os.path.isfile(
        os.path.join("serverConfiguration", "plom.key")
    ) and os.path.isfile(os.path.join("serverConfiguration", "plom-selfsigned.crt")):
        print("SSL key and certificate already exist - will not change.")
        return

    # Command to generate the self-signed key:
    # openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key \
    #          -nodes -out selfsigned.cert -sha256 -days 1000

    # TODO = use os.path.join here.
    sslcmd = (
        "openssl req -x509 -sha256 -newkey rsa:2048 -keyout "
        "serverConfiguration/plom.key -nodes -out "
        "serverConfiguration/plom-selfsigned.crt -days 1000 -subj"
    )

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
    pl = os.path.join("specAndDatabase", "predictionlist.csv")
    if os.path.isfile(pl):
        print("Predictionlist already present.")
        return
    print(
        "Predictionlist will be updated when you run ID-prediction from manager-client."
    )
    with open(pl, "w") as fh:
        fh.write("test, id\n")


def doLatexChecks():
    from plom.server import latex2png, pageNotSubmitted

    os.makedirs("pleaseCheck", exist_ok=True)

    # check build of fragment
    cdir = os.getcwd()
    keepfiles = ("checkThing.png", "pns.0.0.0.png")
    ct = os.path.join(cdir, "pleaseCheck", keepfiles[0])
    pns = os.path.join(cdir, "specAndDatabase", "pageNotSubmitted.pdf")

    fragment = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ worked okay for plom."

    if not latex2png.processFragment(fragment, ct):
        raise PlomServerConfigurationError(
            "Error latex'ing fragment. Please check your latex distribution."
        )

    # build template pageNotSubmitted.pdf just in case needed
    if not pageNotSubmitted.buildPNSPage(pns):
        raise PlomServerConfigurationError(
            "Error building 'pageNotSubmitted.pdf' template page. Please check your latex distribution."
        )

    # Try building a replacement for missing page.
    if not pageNotSubmitted.buildSubstitute(0, 0, 0):
        raise PlomServerConfigurationError(
            "Error building replacement for missing page."
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
    print("Do simple existance checks on required files.")
    checkSpecAndDatabase()
    print("Build required directories")
    buildRequiredDirectories()
    print("Building self-signed ssl keys for server")
    buildSSLKeys()
    print("Copy server networking configuration template into place.")
    createServerConfig()
    print("Build blank predictionlist for identifying.")
    createBlankPredictions()
    print("Do latex checks and build 'pageNotSubmitted.pdf' in case needed")
    doLatexChecks()


#################


def processUsers(userFile, demo, auto):
    # if we have been passed a userFile then process it and return
    if userFile:
        print("Processing user file '{}' to 'userList.json'".format(userFile))
        if os.path.isfile(Path("serverConfiguration") / "userList.json"):
            print("WARNING - this will overwrite the existing userList.json file.")
        from plom.server import manageUserFiles

        manageUserFiles.parseUserlist(userFile)
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
        manageUserFiles.parseUserlist(rawfile)
        return

    if auto is not None:
        print("Creating an auto-generated user list at userListRaw.csv.")
        print(
            "Please edit as you see fit and then rerun 'plom-server users serverConfiguration/userListRaw.csv'"
        )
        from plom.server import manageUserFiles

        # grab required users and regular users
        lst = manageUserFiles.buildCannedUsers(auto)
        print("lst = {}".format(lst))
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

    if os.path.isfile(os.path.join("specAndDatabase", "predictionlist.csv")):
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


def launchTheServer():
    from plom.server import theServer

    if prelaunchChecks():
        theServer.launch()


#################

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(help="sub-command help", dest="command")
#
spI = sub.add_parser("init", help="Initialise server.")
spL = sub.add_parser("class", help="Read in a classlist.")
spU = sub.add_parser("users", help="Create required users.")
spR = sub.add_parser("launch", help="Launch server.")
#
spL.add_argument(
    "classlist",
    nargs="?",
    help="Process the given classlist file and copy the result into place.",
)
spL.add_argument(
    "--demo",
    action="store_true",
    help="Use demo classlist. **DO NOT DO THIS ON REAL SERVER**",
)
##
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


# Now parse things
args = parser.parse_args()

if args.command == "init":
    initialiseServer()
elif args.command == "class":
    # process the class list and copy into place
    processClasslist(args.classlist, args.demo)
elif args.command == "users":
    # process the class list and copy into place
    processUsers(args.userlist, args.demo, args.auto)
elif args.command == "launch":
    launchTheServer()
else:
    parser.print_help()
    print("\n>> Running the plom server <<")
    print(
        "0. Decide on a working directory for the server and cd into it - this need not be the same directory where you started the project."
    )
    print(
        "1. Copy the `specAndDatabase` directory (not just its contents) to your server directory. The `specAndDatabase` directory should be in the directory where you started the project and built PDFs."
    )
    print(
        "1a. If you did not prepare the classlist earlier, then run 'plom-server class <filename>'."
    )
    print(
        "2. Run 'plom-server init' - this will check that everything is in place and create necessary sub-directories **and** create config files for you to edit."
    )
    print(
        "3. Run 'plom-server users' - This will create a template user list file for you to edit. Passwords are displayed in plain text. Running with '--demo' option creates a (standard) demo user list, while '--auto N' makes an random-generated list of N users. Edit as you see fit."
    )
    print(
        "4. Run 'plom-servers users <filename>' - This parses the plain-text user list, performs some simple sanity checks and then hashes the passwords to a new file."
    )
    print("4a. Optionally you can now delete the file containing plain-text passwords.")
    print("5. Now you can start the server with 'plom-server launch'")
    print("FUTURE - 'plom-server stop' will stop the server.")

exit(0)
