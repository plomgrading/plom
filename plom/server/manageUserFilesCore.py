# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2024 Colin B. Macdonald

import json
from pathlib import Path

from plom.manage_user_files import get_raw_user_dict_from_csv
from plom.server import confdir
from plom.server.authenticate import basic_username_password_check
from plom.server.authenticate import SimpleAuthorityHasher


list_of_required_users = ["manager", "scanner", "reviewer"]
minimum_number_of_required_users = 4


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


def parse_and_save_user_list(user_file_path, basedir=Path(".")):
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
    check_and_save_user_list(
        get_raw_user_dict_from_csv(user_file_path), basedir=basedir
    )


def check_and_save_user_list(username_password_dict, basedir=Path(".")):
    """Check and saves userlist and the hashed passwords.

    Do some checking of users/password rules.  Then get the hashed password
    dictionary and saves it.

    Arguments:
        username_password_dict (dict): keys are names and values passwords.
        basedir (pathlib.Path): the usernames and hashed passwords are
            written to `basedir/serverConfiguration/bootstrap_initial_users.json`
            where basedir defaults to "." if omitted.

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
    save_initial_user_list(username_password_dict, basedir=basedir)


def save_initial_user_list(username_password_dict, basedir=Path(".")):
    """Save userlist and the hashed passwords.

    Compute hashed passwords and save them to the initial user list file.

    Arguments:
        username_password_dict (dict): keys are names and values passwords.
        basedir (pathlib.Path): the usernames and hashed passwords are
            written to `basedir/serverConfiguration/bootstrap_initial_users.json`
            where basedir defaults to "." if omitted.

    Returns:
        None: has side effect of saving user hash dictionary.

    Raises:
        ValueError
    """
    basedir = Path(basedir)
    if not check_username_password_format(username_password_dict):
        raise ValueError("Username and passwords are not in the required format.")

    username_hash_dict = make_password_hashes(username_password_dict)

    where = basedir / confdir
    where.mkdir(exist_ok=True)
    with open(where / "bootstrap_initial_users.json", "w") as fh:
        fh.write(json.dumps(username_hash_dict, indent=2))
