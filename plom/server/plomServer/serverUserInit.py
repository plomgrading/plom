# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import hashlib
import json
import os
import uuid
import logging

log = logging.getLogger("servUI")

confdir = "serverConfiguration"


def validate(self, user, token):
    """Check the user's token is valid.

    Returns:
        bool
    """
    # log.debug("Validating user {}.".format(user))
    dbToken = self.DB.getUserToken(user)
    if not dbToken:
        log.warning('User "{}" tried a token but we have no such user!'.format(user))
        return False
    r = self.authority.validate_token(token, dbToken)
    # gives None/False/True
    if r is None:
        log.warning(
            'Malformed token from user "{}": client bug? malicious probing?'.format(
                user
            )
        )
    elif not r:
        log.info('User "{}" tried to use a stale or invalid token'.format(user))
    return bool(r)


def InfoShortName(self):
    if self.testSpec is None:
        return [False]
    else:
        return [True, self.testSpec["name"]]


def info_spec(self):
    """Return the exam specification.

    Returns:
        dict/None: the spec dict or None, e.g., when the server
            does not yet have a spec.  This function is not
            authenticated so ask for the public parts of the spec.
    """
    if not self.testSpec:
        return None
    return self.testSpec.get_public_spec_dict()


def reloadUsers(self, password):
    """Reload the user list."""
    # Check user is manager.
    if not self.authority.authoriseUser("manager", password):
        log.warning("Unauthorised attempt to reload users")
        return False
    log.info("Reloading the user list")
    # Load in the user list and check against existing user list for differences
    try:
        with open(os.path.join(confdir, "userList.json")) as data_file:
            newUserList = json.load(data_file)
            # for each user in the new list..
            for u in newUserList:
                if u not in self.userList:
                    # This is a new user - add them in.
                    self.userList[u] = newUserList[u]
                    self.authority.addUser(u, newUserList[u])
                    log.info("Adding new user = {}".format(u))
            # for each user in the old list..
            for u in self.userList:
                if u not in newUserList:
                    # this user has been removed
                    log.info("Removing user = {}".format(u))
                    # Anything out at user should go back on todo pile.
                    self.DB.resetUsersToDo(u)
                    # remove user's authorisation token.
                    self.authority.detoken(u)
    except FileNotFoundError:
        # TODO?  really not even return False?
        pass
    log.debug("Current user list = {}".format(list(self.userList.keys())))
    # return acknowledgement
    return True


def checkPassword(self, user, password):
    """Does user's password match the hashed one on file?"""
    hashed_pwd = self.DB.getUserPasswordHash(user)
    return self.authority.check_password(password, hashed_pwd)


def checkUserEnabled(self, user):
    return self.DB.isUserEnabled(user)


def giveUserToken(self, user, password, clientAPI, client_ver, remote_ip):
    """When a user requests authorisation
    They have sent their name and password
    first check if they are a valid user
    if so then anything that is recorded as out with that user
    should be reset as todo.
    Then pass them back the authorisation token
    (the password is only checked on first authorisation - since slow)
    """
    if clientAPI != self.API:
        return [
            False,
            "API"
            'Plom API mismatch: client "{}" =/= server "{}". Server version is "{}"; please check you have the right client.'.format(
                clientAPI, self.API, self.Version
            ),
        ]

    if not self.checkPassword(user, password):
        log.warning(
            'Invalid password login attempt by "{}" from {}, client ver "{}"'.format(
                user, remote_ip, client_ver
            )
        )
        return [False, "The name / password pair is not authorised"]

    if not self.checkUserEnabled(user):
        log.info('User "{}" logged in but account is disabled by manager'.format(user))
        return [
            False,
            "The name / password pair has been disabled. Contact your instructor.",
        ]

    # Now check if user already logged in - ie has token already.
    if self.DB.userHasToken(user):
        log.debug('User "{}" already has token'.format(user))
        return [False, "UHT", "User already has token."]
    # give user a token, and store the xor'd version.
    [clientToken, storageToken] = self.authority.create_token()
    self.DB.setUserToken(user, storageToken)
    # On token request also make sure anything "out" with that user is reset as todo.
    # We keep this here in case of client crash - todo's get reset on login and logout.
    self.DB.resetUsersToDo(user)
    log.info(
        'Authorising user "{}" from {}, client ver "{}"'.format(
            user, remote_ip, client_ver
        )
    )
    return [True, clientToken]


def setUserEnable(self, user, enableFlag):
    if enableFlag:
        self.DB.enableUser(user)
    else:
        self.DB.disableUser(user)
    return [True]


def createModifyUser(self, username, password):
    # basic sanity check of username / password
    if not self.authority.basic_user_password_check(username, password):
        return [False, "Username/Password fails basic checks."]
    if username == "HAL":  # Don't mess with HAL
        return [False, "I'm sorry, Dave. I'm afraid I can't do that."]
    # hash the password
    passwordHash = self.authority.create_password_hash(password)
    if self.DB.doesUserExist(username):  # user exists, so update password
        if self.DB.setUserPasswordHash(username, passwordHash):
            return [True, False]
        else:
            return [False, "Password update error."]
    else:  # user does not exist, so create them
        if self.DB.createUser(username, passwordHash):
            return [True, True]
        else:
            return [False, "User creation error."]


def closeUser(self, user):
    """Client is closing down their app, so remove the authorisation token"""
    log.info("Revoking auth token from user {}".format(user))
    self.DB.clearUserToken(user)
    # make sure all their out tasks are returned to "todo"
    self.DB.resetUsersToDo(user)
