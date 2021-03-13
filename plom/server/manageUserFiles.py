# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

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


def build_canned_users(number_of_users, numbered=False):
    """Creates a list of fake users.

    Arguments:
        number_of_users (int): number of fake users to create.
        numbered (bool): if True, make numbered users such as "user017"
            otherwise (default) make real-ish names like "gwen" or
            "talia07".

    Returns:
        list: list of users (either named or numbered users).
    """
    # build list of required users
    user_list = []
    for required_user in list_of_required_users:
        user_list.append([required_user, simple_password(n=4)])

    # append list of standard users
    if numbered:
        user_list.extend(make_numbered_user_list(number_of_users))
    else:
        user_list.extend(make_random_user_list(number_of_users))

    return user_list


def return_user_hash(username_password_dict):
    """Creates a dictionary for username and hash which is derived from the user's password.

    TODO: Would be really nice if the hash function was somehow passed in as a parameter.

    Arguments:
        username_password_dict (dict):  keys username (str) to value
            password (str).

    Returns:
        dict: keys username (str) to value hashed password (str).
    """
    username_hash_dict = {}
    for user in username_password_dict:
        username_hash_dict[user] = plomctx.hash(username_password_dict[user])
    return username_hash_dict


def check_username_password_format(username_password_dict):
    """Checks that the username-passwords are valid and to a specific standard.

    TODO: More checks could be added, Could be cleaned up further.

    May not check all the data: short-circuits out on first false.

    Arguments:
        username_password_dict (dict): keys username (str) to value
            password (str).

    Returns:
        boolean: also prints to screen as a side effect.
    """
    for username, password in username_password_dict.items():
        if not (username.isalnum() and username[0].isalpha()):
            print(
                "Username '{}' is problematic: should be alphanumeric and starting with a letter.".format(
                    username
                )
            )
            return False
        if len(password) < 4:
            print(
                "Password of '{}' is too short, should be at least 4 chars.".format(
                    username
                )
            )
            return False
        if password == username:
            print("Password of '{}' is too close to their username.".format(username))
            return False
    return True


def check_user_file_header(csv_headers):
    """Checks the headers in csv_headers to make sure it has the reaquired headers.

    Currently (username,password) format, but can be changed in the future.

    Arguments:
        csv_headers (list): headers (str), typically from a csv file.

    Returns:
        boolean
    """
    if csv_headers != list_of_expected_header:
        return False
    return True


def check_usernames_requirements(username_password_dict):
    """Check for minimum requires users.

    Check we have manager, scanner and reviewer + at least 1 regular
    user.

    Arguments:
        username_password_dict (dict): keys username (str) to value
            password (str).

    Returns:
        boolean
    """
    if len(username_password_dict) < minimum_number_of_required_users or not all(
        user in username_password_dict for user in list_of_required_users
    ):
        return False
    return True


def return_csv_info(user_file_path):
    """Gets the header and user/password dictionary from the file and returns it.

    Arguments:
        user_file_path (str/pathlib.Path): a csv file of proposed
            usernames and passwords.

    Returns:
        list: strings of the the extracted headers.
        dict: A dict(str:str) which represents (username: password).
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
        user_file_path (str/pathlib.Path): a csv file of proposed
            usernames and passwords.

    Returns:
        None: has side effect of saving user hash dictionary.

    Raises:
        ValueError
    """
    csv_headers, username_password_dict = return_csv_info(user_file_path)

    if not check_user_file_header(csv_headers):
        raise ValueError(
            'Malformed header - should have 2 columns with headers "user" and "password".'
        )
    if not check_usernames_requirements(username_password_dict):
        raise ValueError(
            "Userlist must contain 'manager', 'scanner', 'reviewer' and at least 1 regular user."
        )
    if not check_username_password_format(username_password_dict):
        raise ValueError("Username and passwords are not in the required format.")

    username_hash_dict = return_user_hash(username_password_dict)

    with open(user_hash_login_json_path, "w") as fh:
        fh.write(json.dumps(username_hash_dict, indent=2))
