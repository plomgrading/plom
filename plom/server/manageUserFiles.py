# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

import csv
import json

from .aliceBob import simple_password, make_random_user_list, make_numbered_user_list


# TODO - instead of running a cryptocontext here - move stuff into authenticate.py?
# Stuff for hashing and verifying passwords
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext

# These parameters are used for processing and creating the user login info
plomctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
user_hash_login_json_path = "serverConfiguration/userList.json"
list_of_required_users = ["manager", "scanner", "reviewer"]
list_of_expected_header = ["user", "password"]
minimum_number_of_required_users = 4
cutoff_for_named_users = 20
cutoff_for_numbered_users = 50


def build_canned_users(number_of_users):
    """Creates a list of fake users.

    Arguments:
        number_of_users {int} -- Number of fake users to create.

    Returns:
        list -- List of users (either named or numbered users).
    """
    if number_of_users == 0:
        print("Must produce at least 1 regular user. Aborting.")
        exit(1)

    # build list of required users
    user_list = []
    for required_user in list_of_required_users:
        user_list.append([required_user, simple_password()])
    # now append list of standard users - some sanity checks about numbers
    if number_of_users <= cutoff_for_named_users:
        print("Making list of named users")
        user_list = user_list + make_random_user_list(number_of_users)
    elif number_of_users <= cutoff_for_numbered_users:
        print("Making list of numbered users")
        user_list = user_list + make_numbered_user_list(number_of_users)
    else:
        print(
            "This is too many canned users. You should make your own list of users. Aborting."
        )
        exit(1)

    return user_list


def save_users(username_hash_dict, user_hash_login_json_path):
    """Saves the user hash login info to the file at user_hash_login_json_path.

    Arguments:
        username_hash_dict {dict} -- Dictionary of the form {Str:Str} which represents
                                     {username: hashed_password} objects.
        user_hash_login_json_path {Str} -- File path for saving the login hash info.
    """

    with open(user_hash_login_json_path, "w") as fh:
        fh.write(json.dumps(username_hash_dict, indent=2))


def return_user_hash(username_password_dict):
    """Creates a dictionary for username and hash which is derived from the user's password.

    TODO: Would be really nice if the hash function was somehow passed in as a parameter.

    Arguments:
        username_password_dict {dict} -- A dictionary of the form {Str:Str} which represents
                                        {username: password} objects.

    Returns:
        dict -- A dictionary of the form {Str:Str} which represents {username: hashed_password}
                objects.
    """

    username_hash_dict = {}
    for user in username_password_dict:
        username_hash_dict[user] = plomctx.hash(username_password_dict[user])
    return username_hash_dict


def check_username_password_format(username_password_dict):
    """Checks that the username-passwords are valid and to a specific standard.

    Must be done after the header file checks and the username checks.
    TODO: More checks could be added, Could be cleaned up further.

    Arguments:
        username_password_dict {dict} -- A dict(Str:Str) which represents (username: password).

    Returns:
        boolean -- True/False
    """

    for username, password in username_password_dict.items():

        # basic sanity check of username
        if not (len(username) >= 4 and username.isalnum()):
            print(
                "Usernames must be at least 4 alphanumeric characters. Username '{}' is problematic.".format(
                    username
                )
            )
            return False

        # basic password checks
        if len(password) < 4 or username in password:
            print(
                "Passwords must be at least 4 characters and cannot contain the username. Password of '{}' is problematic.".format(
                    username
                )
            )
            return False

    return True


def check_user_file_header(csv_headers):
    """Checks the headers in csv_headers to make sure it has the reaquired headers.

    Currently (username,password) format, but can be changed in the future.

    Arguments:
        csv_headers {list} -- List[Str] having the headers in the csv file.

    Returns:
        boolean -- True/False
    """

    if csv_headers != list_of_expected_header:
        return False

    return True


def check_usernames_requirements(username_password_dict):
    """Check for minimum requires users.

    Must be run before check_user_file_header.

    Arguments:
        username_password_dict {dict} -- A dict(Str:Str) which represents (username: password).

    Returns:
        boolean -- True/False
    """

    # check we have manager, scanner and reviewer + at least 1 regular user.
    if len(username_password_dict) < minimum_number_of_required_users or not all(
        user in username_password_dict for user in list_of_required_users
    ):
        return False

    return True


def return_csv_info(user_file_path):
    """Gets the header and user/password dictionary from the file and returns it.

    Arguments:
        user_file_path {Str} -- Path to the user files.

    Returns:
        list -- List[Str] which represents the extracted headers.
        dict -- A dict(Str:Str) which represents (username: password).
    """

    csv_headers = []
    username_password_dict = {}

    with open(user_file_path, "r") as save_file:
        reader = csv.reader(save_file, skipinitialspace=True)

        # first line should be just header
        csv_headers = next(reader, None)

        for row in reader:
            username_password_dict[row[0]] = row[1]

    return csv_headers, username_password_dict


def parse_user_list(user_file_path):
    """Parses the user list provided and saves the user hash dictionary.

    1. Reads the header and username/password dictionary in the user_file_path.
    2. Checks the header and minimum requirements in term of user types and number.
    3. Check the password and username format requirements.
    4. Gets the Hash dictionary and saves it.

    Arguments:
        user_file_path {Str} -- Path to the user files.
    """
    # First we get the csv info
    csv_headers, username_password_dict = return_csv_info(user_file_path)

    if not check_user_file_header(csv_headers):
        print(
            'Malformed header in user_file_path - should have 2 columns with headers "user" and "password". Aborting.'
        )
        exit(1)
    elif not check_usernames_requirements(username_password_dict):
        print(
            "Userlist must contain 'manager', 'scanner', 'reviewer' and at least 1 regular user."
        )
        exit(1)
    elif not check_username_password_format(username_password_dict):
        print("Username and passwords are not in the required format.")
        exit(1)
    else:
        username_hash_dict = return_user_hash(username_password_dict)

    save_users(username_hash_dict, user_hash_login_json_path)
