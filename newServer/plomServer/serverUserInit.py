import hashlib
import os
import uuid

# this allows us to import from ../resources
import sys

sys.path.append("..")
from resources.logIt import printLog


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
        printLog("SUI", "Unauthorised attempt to reload users")
        return False
    printLog("SUI", "Reloading the user list")
    # Load in the user list and check against existing user list for differences
    if os.path.exists("../resources/userList.json"):
        with open("../resources/userList.json") as data_file:
            newUserList = json.load(data_file)
            # for each user in the new list..
            for u in newUserList:
                if u not in self.userList:
                    # This is a new user - add them in.
                    self.userList[u] = newUserList[u]
                    self.authority.addUser(u, newUserList[u])
                    printLog("SUI", "Adding new user = {}".format(u))
            # for each user in the old list..
            for u in self.userList:
                if u not in newUserList:
                    # this user has been removed
                    printLog("SUI", "Removing user = {}".format(u))
                    # Anything out at user should go back on todo pile.
                    self.DB.resetUsersToDo(u)
                    # remove user's authorisation token.
                    self.authority.detoken(u)
    printLog("SUI", "Current user list = {}".format(list(self.userList.keys())))
    # return acknowledgement
    return True


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
    # check password
    if self.authority.checkPassword(user, password):
        # Now check if user already logged in - ie has token already.
        if self.authority.userHasToken(user):
            return [False, "UHT", "User already has token."]
        # give user a token.
        self.authority.allocateToken(user)
        # On token request also make sure anything "out" with that user is reset as todo.
        # We keep this here in case of client crash - todo's get reset on login and logout.
        self.DB.resetUsersToDo(user)
        printLog("SUI", "Authorising user {}".format(user))
        return [True, self.authority.getToken(user)]
    else:
        return [False, "The name / password pair is not authorised".format(user)]


def closeUser(self, user):
    """Client is closing down their app, so remove the authorisation token
    """
    printLog("SUI", "Revoking auth token from user {}".format(user))
    self.authority.detoken(user)
    # make sure all their out tasks are returned to "todo"
    self.DB.resetUsersToDo(user)
