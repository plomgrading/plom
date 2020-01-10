import hashlib
import os
import uuid


def InfoShortName(self):
    if self.testSpec is None:
        return [False]
    else:
        return [True, self.testSpec["name"]]


def InfoQuestionsVersions(self):
    if self.testSpec is None:
        return [False]
    else:
        return [
            True,
            self.testSpec["numberOfQuestions"],
            self.testSpec["numberOfVersions"],
        ]


def InfoPQV(self):
    if self.testSpec is None:
        return [False]
    else:
        return [
            True,
            self.testSpec["numberOfPages"],
            self.testSpec["numberOfQuestions"],
            self.testSpec["numberOfVersions"],
        ]


def InfoTPQV(self):
    if self.testSpec is None:
        return [False]
    else:
        return [
            True,
            self.testSpec["numberToProduce"],
            self.testSpec["numberOfPages"],
            self.testSpec["numberOfQuestions"],
            self.testSpec["numberOfVersions"],
        ]


def reloadUsers(self, password):
    """Reload the user list."""
    # Check user is manager.
    if not self.authority.authoriseUser("manager", password):
        print("Unauthorised attempt to reload users")
        return False
    print("Reloading the user list")
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
                    print("New user = {}".format(u))
            # for each user in the old list..
            for u in self.userList:
                if u not in newUserList:
                    # this user has been removed
                    print("Removing user = {}".format(u))
                    # Anything out at user should go back on todo pile.
                    self.DB.resetUsersToDo(u)
                    # remove user's authorisation token.
                    self.authority.detoken(u)
    print("Current user list = {}".format(list(self.userList.keys())))
    # return acknowledgement
    print(">> User list reloaded")
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

    if self.authority.authoriseUser(user, password):
        # On token request also make sure anything "out" with that user is reset as todo.
        self.DB.resetUsersToDo(user)
        print("Authorising user {}".format(user))
        return [True, self.authority.getToken(user)]
    else:
        return [False, "The name / password pair is not authorised".format(user)]


def closeUser(self, user):
    """Client is closing down their app, so remove the authorisation token
    """
    self.authority.detoken(user)
