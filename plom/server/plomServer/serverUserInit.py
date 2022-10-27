# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2022 Edith Coates

import logging

log = logging.getLogger("servUI")

confdir = "serverConfiguration"


def validate(self, user, token):
    """Check the user's token is valid.

    Returns:
        bool
    """
    # log.debug(f'Validating user "{user}"')
    try:
        dbToken = self.DB.getUserToken(user)
    except ValueError:
        log.warning(f'User "{user}" tried a token but we have no such user!')
        return False
    if not dbToken:
        log.info(f'User "{user}" tried a token but they are not logged in')
        return False
    r = self.authority.validate_token(token, dbToken)
    # gives None/False/True
    if r is None:
        log.warning(
            f'User "{user}" tried a malformed token: client bug? malicious probing?'
        )
    elif not r:
        log.info(f'User "{user}" tried to use a stale or invalid token')
    return bool(r)


def InfoShortName(self):
    if self.testSpec is None:
        return None
    return self.testSpec["name"]


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


def checkPassword(self, user, password):
    """Does user's password match the hashed one on file?"""
    hashed_pwd = self.DB.getUserPasswordHash(user)
    return self.authority.check_password(password, hashed_pwd)


def checkUserEnabled(self, user):
    return self.DB.isUserEnabled(user)


def giveUserToken(self, user, password, clientAPI, client_ver, remote_ip):
    """Verify a user's password and give them back a token for quicker future actions.

    When a user requests authorisation
    They have sent their name and password
    first check if they are a valid user
    if so then anything that is recorded as out with that user
    should be reset as todo.
    Then pass them back the authorisation token
    (the password is only checked on first authorisation - since slow)

    returns:
        tuple: `(True, token)` on success, `(False, code, user_readable)`
        on failure.  Here `code` can be one of the strings "API",
        "NotAuth", "Disabled", "HasToken" and `user_readable` is a
        longer string appropriate for an user-centred error message.
    """
    if clientAPI != self.API:
        return (
            False,
            "API",
            'Plom API mismatch: client "{}" =/= server "{}". Server version is "{}"; please check you have the right client.'.format(
                clientAPI, self.API, self.Version
            ),
        )

    if not self.checkPassword(user, password):
        log.warning(
            'Invalid password login attempt by "{}" from {}, client ver "{}"'.format(
                user, remote_ip, client_ver
            )
        )
        return (False, "NotAuth", "The name / password pair is not authorised")

    if not self.checkUserEnabled(user):
        log.info('User "{}" logged in but account is disabled by manager'.format(user))
        return (
            False,
            "Disabled",
            "User login has been disabled. Contact your administrator?",
        )

    # Now check if user already logged in - ie has token already.
    if self.DB.userHasToken(user):
        log.debug('User "{}" already has token'.format(user))
        return (
            False,
            "HasToken",
            "User already has token: perhaps logged in elsewhere or previous session crashed?",
        )
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
    return (True, clientToken)


def setUserEnable(self, user, enableFlag):
    if enableFlag:
        self.DB.enableUser(user)
    else:
        self.DB.disableUser(user)
    return [True]


def createUser(self, username, password):
    r, msg = self.authority.basic_username_password_check(username, password)
    if not r:
        return [False, f"Username/Password fails basic checks: {msg}"]
    if username == "HAL":  # Don't mess with HAL
        return [False, "I'm sorry, Dave. I'm afraid I can't do that."]

    if self.DB.doesUserExist(username):
        return [False, "User already exists."]

    passwordHash = self.authority.create_password_hash(password)
    if self.DB.createUser(username.lower(), passwordHash):
        return [True, True]

    return [False, "User creation error."]


def changeUserPassword(self, username, password):
    r, msg = self.authority.basic_username_password_check(username, password)
    if not r:
        return [False, f"Username/Password fails basic checks: {msg}"]
    if username == "HAL":  # Don't mess with HAL
        return [False, "I'm sorry, Dave. I'm afraid I can't do that."]

    if not self.DB.doesUserExist(username):
        return [False, "User does not exist."]

    passwordHash = self.authority.create_password_hash(password)
    update_result = self.DB.setUserPasswordHash(username, passwordHash)
    if update_result:
        return [True, True]
    else:
        return [False, "Password update error."]


def closeUser(self, user):
    """Client is closing down their app, so remove the authorisation token"""
    log.info("Revoking auth token from user {}".format(user))
    self.DB.clearUserToken(user)
    # make sure all their out tasks are returned to "todo"
    self.DB.resetUsersToDo(user)
