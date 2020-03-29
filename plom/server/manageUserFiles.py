__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import csv
import json

from .aliceBob import simplePassword, makeRandomUserList, makeNumberedUserList


# TODO - instead of running a cryptocontext here - move stuff into authenticate.py?
# Stuff for hashing and verifying passwords
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext

# Fire up password stuff
plomctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def buildCannedUsers(number):
    if number == 0:
        print("Must produce at least 1 regular user. Aborting.")
        exit(1)

    # build list of required users
    lst = []
    for n in ["manager", "scanner", "reviewer"]:
        lst.append([n, simplePassword()])
    # now append list of standard users - some sanity checks about numbers
    if number <= 20:
        print("Making list of named users")
        lst = lst + makeRandomUserList(number)
    elif number <= 50:
        print("Making list of numbered users")
        lst = lst + makeNumberedUserList(number)
    else:
        print(
            "This is too many canned users. You should make your own list of users. Aborting."
        )
        exit(1)

    return lst


def checkNamePassword(u, p):
    # basic sanity check of username and password
    # username checks
    if not (len(u) >= 4 and u.isalnum()):
        print(
            "Usernames must be at least 4 alphanumeric characters. Username '{}' is problematic.".format(
                u
            )
        )
        return False

    # basic password checks
    if len(p) < 4 or u in p:
        print(
            "Passwords must be at least 4 characters and cannot contain the username. Password of '{}' is problematic.".format(
                u
            )
        )
        return False

    return True


def saveUsers(userHash):
    with open("serverConfiguration/userList.json", "w") as fh:
        fh.write(json.dumps(userHash, indent=2))


def parseUserlist(userFile):
    userRaw = {}
    userHash = {}
    # read file to dict
    with open(userFile, "r") as fh:
        reader = csv.reader(fh, skipinitialspace=True)
        # first line should be just header
        headers = next(reader, None)
        if headers != ["user", "password"]:
            print(
                'Malformed header in userfile - should have 2 columns with headers "user" and "password". Aborting.'
            )
            exit(1)
        for row in reader:
            userRaw[row[0]] = row[1]

    # check we have manager, scanner and reviewer + at least 1 regular user.
    if (
        all(u in userRaw for u in ["manager", "scanner", "reviewer"])
        and len(userRaw) < 4
    ):
        print(
            "Userlist must contain 'manager', 'scanner', 'reviewer' and 1 regular user."
        )
        exit(1)

    for u in userRaw:
        if checkNamePassword(u, userRaw[u]):
            print("Encoding password for user {}".format(u))
            userHash[u] = plomctx.hash(userRaw[u])
        else:
            exit(1)

    saveUsers(userHash)
