__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import csv
import json

from .aliceBob import simple_password, make_random_user_list, make_numbered_user_list


# TODO - instead of running a cryptocontext here - move stuff into authenticate.py?
# Stuff for hashing and verifying passwords
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext

# Fire up password stuff
plomctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def build_canned_users(number):
    """Creates a list of fake users.

    Arguments:
        number {int} -- Number of fake users to create.

    Returns:
        list -- List of users (either named or numbered users)
    """
    if number == 0:
        print("Must produce at least 1 regular user. Aborting.")
        exit(1)

    # build list of required users
    lst = []
    for n in ["manager", "scanner", "reviewer"]:
        lst.append([n, simple_password()])
    # now append list of standard users - some sanity checks about numbers
    if number <= 20:
        print("Making list of named users")
        lst = lst + make_random_user_list(number)
    elif number <= 50:
        print("Making list of numbered users")
        lst = lst + make_numbered_user_list(number)
    else:
        print(
            "This is too many canned users. You should make your own list of users. Aborting."
        )
        exit(1)

    return lst


def check_name_password(username, password):
    """Basic sanity check of username and password.

    Arguments:
        username {str} -- Username to check.
        password {str} -- Password to check.

    Returns:
        bool -- True if the password is valid, False otherwise.
    """
    # basic username checks
    if not (len(username) >= 4 and username.isalnum()):
        print(
            "Usernames must be at least 4 alphanumeric characters. Username '{}' is problematic.".format(
                username
            )
        )
        return False

    # basic password checks
    if len(password) < 4:
        print(
            "Passwords must be at least 4 characters. Password of '{}' is problematic.".format(
                password
            )
        )
    elif username in password:
        print(
            "Passwords must not contain the username. Password of '{}' is problematic.".format(
                password
            )
        )
        return False

    return True


def save_users(userHash):
    """Saves all of the users to a json file

    Arguments:
        userHash {hex} -- Information about users to write to json.
    """
    with open("serverConfiguration/userList.json", "w") as fh:
        fh.write(json.dumps(userHash, indent=2))


def parse_user_list(userFile):
    """Parses the user information to a list from a specified file.

    Arguments:
        userFile {str} -- Name of the file containing user information.
    """
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
        if check_name_password(u, userRaw[u]):
            print("Encoding password for user {}".format(u))
            userHash[u] = plomctx.hash(userRaw[u])
        else:
            exit(1)

    save_users(userHash)
