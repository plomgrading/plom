import hashlib
import json
import os
import uuid
import logging

log = logging.getLogger("servUI")

confdir = "serverConfiguration"


def validate(self, user, token):
    """Check the user's token is valid"""
    # log.debug("Validating user {}.".format(user))
    return self.DB.validateToken(user, token)


def InfoShortName(self):
    if self.testSpec is None:
        return [False]
    else:
        return [True, self.testSpec["name"]]


def InfoGeneral(self):
    if self.testSpec is not None:
        return [
            True,
            self.testSpec["name"],
            self.testSpec["numberToProduce"],
            self.testSpec["numberOfPages"],
            self.testSpec["numberOfQuestions"],
            self.testSpec["numberOfVersions"],
            self.testSpec["publicCode"],
        ]
    else:  # this should not happen
        return [False]


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
    # Check the pwd and enabled. Get the hash from DB
    passwordHash = self.DB.getUserPasswordHash(user)
    if self.authority.checkPassword(password, passwordHash):
        # first check if user is enabled, then check pwd.
        if self.DB.isUserEnabled(user):
            return True
    return False


def giveUserToken(self, user, password, clientAPI):
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

    if self.checkPassword(user, password):
        # Now check if user already logged in - ie has token already.
        if self.DB.userHasToken(user):
            log.debug('User "{}" already has token'.format(user))
            return [False, "UHT", "User already has token."]
        # give user a token.
        token = self.authority.createToken()
        self.DB.setUserToken(user, token)
        # On token request also make sure anything "out" with that user is reset as todo.
        # We keep this here in case of client crash - todo's get reset on login and logout.
        self.DB.resetUsersToDo(user)
        log.info('Authorising user "{}"'.format(user))
        return [True, token]
    else:
        return [False, "The name / password pair is not authorised".format(user)]


def toggleEnableDisableUser(self, user):
    if self.DB.isUserEnabled(user):
        self.DB.disableUser(user)
    else:
        self.DB.enableUser(user)
    return [True]


def closeUser(self, user):
    """Client is closing down their app, so remove the authorisation token
    """
    log.info("Revoking auth token from user {}".format(user))
    self.DB.clearUserToken(user)
    # make sure all their out tasks are returned to "todo"
    self.DB.resetUsersToDo(user)
