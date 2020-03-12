#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import locale
import os
import shlex
import shutil
import subprocess

# import tools for dealing with resource files
import pkg_resources

from plom import SpecVerifier, SpecParser

#################
def processClasslist(fname, demo):
    os.makedirs("specAndDatabase", exist_ok=True)
    # check if classlist.csv is in place - if so abort.
    if os.path.isfile(os.path.join("specAndDatabase", "classlist.csv")):
        print(
            "Classlist file already present in 'specAndDatabase' directory. Aborting."
        )
        exit(0)

    if demo:
        print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
        cl = pkg_resources.resource_string("plom", "demoClassList.csv")
        cl = cl.decode()
        with open(os.path.join("specAndDatabase", "classlist.csv"), "w+") as fh:
            fh.write(cl)
        return

    from plom.produce import buildClasslist

    # check if a filename given
    if fname is None:
        print("Please provide a classlist file.")
        buildClasslist.acceptedFormats()
        exit(1)
    # grab the file, process it and copy it into place.

    if os.path.isfile(fname):
        buildClasslist.getClassList(fname)
    else:
        print('Cannot find file "{}"'.format(fname))
        exit(1)


def checkSpecAndDatabase():
    if os.path.isdir("specAndDatabase"):
        print("Directory 'specAndDatabase' is present.")
    else:
        print(
            "Cannot find 'specAndDatabase' - you must copy this into place before running server. Cannot continue."
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
        print("Cannot find the classlist. Aborting.")
        print(
            "You do not have to return to 'plom-build'. To process a classlist please run 'plom-server class <filename>'"
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
    try:
        for dir in lst:
            os.makedirs(dir, exist_ok=True)
    except Exception as err:
        print("Something went wrong building directories. Cannot continue.")
        exit(1)


def buildSSLKeys():
    # Command to generate the self-signed key:
    # openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key \
    #          -nodes -out selfsigned.cert -sha256 -days 1000

    # TODO = use os.path.join here.
    sslcmd = (
        "openssl req -x509 -sha256 -newkey rsa:2048 -keyout "
        "serverConfiguration/mlp.key -nodes -out "
        "serverConfiguration/mlp-selfsigned.crt -days 1000 -subj"
    )
    sslcmd += " '/C={}/ST=./L=./CN=localhost'".format(locale.getdefaultlocale()[0][-2:])
    try:
        subprocess.check_call(shlex.split(sslcmd))
    except Exception as err:
        print("Something went wrong building ssl keys.")
        print(err)
        print("Cannot continue.")
        exit(1)


def createServerConfig():
    template = pkg_resources.resource_string("plom", "serverDetails.toml")
    template = template.decode()
    with open(os.path.join("serverConfiguration", "serverDetails.toml"), "w+") as fh:
        fh.write(template)
    print(
        "Please update the 'serverConfiguration/serverDetails.toml' file with the correct name (or IP) of your server and the port for communications."
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


#################


def processUsers(userFile, demo, auto):
    # if we have been passed a userFile then process it and return
    if userFile is not None:
        print("Processing user file '{}'".format(userFile))
        print("WARNING - this will overwrite any existing userList.json file.")
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
        print(
            "Please edit as you see fit and then rerun 'plom-server users serverConfiguration/userListRaw.csv'"
        )
        cl = pkg_resources.resource_string("plom", "demoUserList.csv")
        cl = cl.decode()
        with open(os.path.join("serverConfiguration", "userListRaw.csv"), "w+") as fh:
            fh.write(cl)
        return
    if auto is not None:
        print("Creating an auto-generated user list at userListRaw.csv.")
        print(
            "Please edit as you see fit and then rerun 'plom-server user serverConfiguration/userListRaw.csv'"
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

    if userFile is None:
        print(
            "Creating 'serverConfiguration/userListRaw.csv' - please edit passwords for 'manager', 'scanner', 'reviewer', and then add one or more normal users and their passwords. Note that passwords must be at least 4 characters and usernames should be at least 4 alphanumeric characters."
        )
        cl = pkg_resources.resource_string("plom", "templateUserlist.csv")
        cl = cl.decode()
        with open(os.path.join("serverConfiguration", "userListRaw.csv"), "w+") as fh:
            fh.write(cl)


#################
def launchTheServer():
    from plom.server import newServer

    newServer.launch()


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
print(args)

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
