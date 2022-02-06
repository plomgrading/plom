# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

import csv
import json
from pathlib import Path
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import plom
from plom.server import confdir
from plom.server.authenticate import basic_username_password_check
from plom.server.authenticate import SimpleAuthorityHasher
from plom.aliceBob import (
    simple_password,
    make_random_user_list,
    make_numbered_user_list,
)


list_of_required_users = ["manager", "scanner", "reviewer"]
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


def make_password_hashes(username_password_dict):
    """Creates a dictionary for username and hash which is derived from the user's password.

    TODO: Would be really nice if the hash function was somehow passed in as a parameter.

    Arguments:
        username_password_dict (dict):  keys username (str) to value
            password (str).

    Returns:
        dict: keys username (str) to value hashed password (str).
    """
    hasher = SimpleAuthorityHasher()
    username_hash_dict = {}
    for user, pwd in username_password_dict.items():
        username_hash_dict[user] = hasher.create_password_hash(pwd)
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
        r, msg = basic_username_password_check(username, password)
        if not r:
            print(f"Username '{username}': {msg}")
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


def get_raw_user_dict_from_csv(user_file_path):
    """Gets the user/password dictionary from a csv file.

    Arguments:
        user_file_path (str/pathlib.Path): a csv file of proposed
            usernames and passwords.

    Returns:
        dict: A dict(str:str) which represents (username: password).

    Raises:
        ValueError: malformed csv file.
    """
    with open(user_file_path, "r") as f:
        return _get_raw_user_dict(f)


def _get_raw_user_dict(f):
    username_password_dict = {}
    reader = csv.reader(f, skipinitialspace=True)
    csv_headers = next(reader, None)
    if csv_headers != ["user", "password"]:
        raise ValueError('csv file must have two columns "user" and "password".')
    for row in reader:
        username_password_dict[row[0]] = row[1]
    return username_password_dict


def get_template_user_list():
    """Gets the user/password dictionary for some fixed demo values."""
    with resources.open_text(plom, "templateUserList.csv") as f:
        return _get_raw_user_dict(f)


def write_template_csv_user_list(filename):
    """Save a csv file of fixed demo usernames and nonhashed passwords."""
    b = resources.read_binary(plom, "templateUserList.csv")
    with open(filename, "wb") as f:
        f.write(b)


def parse_and_save_user_list(user_file_path):
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
    save_user_list(get_raw_user_dict_from_csv(user_file_path))


def save_user_list(username_password_dict, basedir=Path(".")):
    """Saves userlist and their hashed passwords.

    Do some checking of users/password rules.  Then get the hashed password
    dictionary and saves it.

    Arguments:
        username_password_dict (dict): keys are names and values passwords.
        basedir (pathlib.Path): the usernames and hashed passwords are
            written to `basedir/serverConfiguration/userList.json` where
            basedir defaults to "." if omitted.

    Returns:
        None: has side effect of saving user hash dictionary.

    Raises:
        ValueError
    """
    basedir = Path(basedir)
    if not check_usernames_requirements(username_password_dict):
        raise ValueError(
            "Userlist must contain 'manager', 'scanner', 'reviewer' and at least 1 regular user."
        )
    if not check_username_password_format(username_password_dict):
        raise ValueError("Username and passwords are not in the required format.")

    username_hash_dict = make_password_hashes(username_password_dict)

    where = basedir / confdir
    where.mkdir(exist_ok=True)
    with open(where / "userList.json", "w") as fh:
        fh.write(json.dumps(username_hash_dict, indent=2))
