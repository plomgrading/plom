# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from datetime import datetime
import logging

import peewee as pw

from plom.db.tables import plomdb
from plom.db.tables import IDGroup, QGroup, User


log = logging.getLogger("DB")


def createUser(self, uname, passwordHash):
    try:
        User.create(
            name=uname,
            password=passwordHash,
            last_activity=datetime.now(),
            last_action="Created",
        )
    except pw.IntegrityError as e:
        log.error("Create User {} error - {}".format(uname, e))
        return False
    return True


def doesUserExist(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    else:
        return True


def setUserPasswordHash(self, uname, passwordHash):
    # Don't mess with HAL
    if uname == "HAL":
        return False
    # token generated by server not DB
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    with plomdb.atomic():
        uref.password = passwordHash
        uref.last_activity = datetime.now()
        uref.last_action = "Password set"
        uref.save()
    return True


def getUserPasswordHash(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return None
    else:
        return uref.password


def isUserEnabled(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    else:
        return uref.enabled


def enableUser(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    with plomdb.atomic():
        uref.enabled = True
        uref.save()
    return True


def disableUser(self, uname):
    # when user is disabled we should set the enabled flag to false, remove their auth-token and then remove all their todo-stuff.
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    # set enabled flag to false and remove their token
    with plomdb.atomic():
        uref.enabled = False
        uref.token = None
        uref.save()
    # put all of user's tasks back on the todo pile.
    self.resetUsersToDo(uname)
    return True


def setUserToken(self, uname, token, msg="Log on"):
    # token generated by server not DB
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    with plomdb.atomic():
        uref.token = token
        uref.last_activity = datetime.now()
        uref.last_action = msg
        uref.save()
    return True


def clearUserToken(self, uname):
    return self.setUserToken(uname, None, "Log off")


def getUserToken(self, uname):
    """Return user's saved token or None if logged out.

    args:
        uname (str): username.

    returns:
        str/None: user's token or None if use is not logged in.

    raises:
        ValueError: no such user.
    """
    uref = User.get_or_none(name=uname)
    if uref is None:
        raise ValueError("No such user")
    return uref.token


def userHasToken(self, uname):
    """Return user's saved token or None if logged out.

    args:
        uname (str): username.

    returns:
        bool: True if the user has a token.

    raises:
        ValueError: no such user.
    """
    if self.getUserToken(uname) is not None:
        return True
    else:
        return False


def validateToken(self, uname, token):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return False
    if uref.token == token:
        return True
    else:
        return False


def getUserList(self):
    rval = []
    for uref in User.select():
        rval.append(uref.name)
    return rval


def getUserDetails(self):
    rval = {}
    for uref in User.select():
        val = [False, False]
        if uref.enabled:
            val[0] = True
        if uref.token is not None:
            val[1] = True
        if uref.last_activity is None:
            val += ["", ""]
        else:
            val += [
                uref.last_activity.strftime("%y:%m:%d-%H:%M:%S"),
                uref.last_action,
            ]
        rval[uref.name] = val + self.RgetUserFullProgress(uref.name)
    return rval


def resetUsersToDo(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return
    with plomdb.atomic():
        query = IDGroup.select().where(IDGroup.user == uref, IDGroup.status == "out")
        for x in query:
            x.status = "todo"
            x.user = None
            x.time = datetime.now()
            x.save()
            log.info("Reset user {} ID task {}".format(uname, x.group.gid))
    with plomdb.atomic():
        query = QGroup.select().where(
            QGroup.user == uref,
            QGroup.status == "out",
        )
        for x in query:
            x.status = "todo"
            x.user = None
            # now clean up the qgroup
            # TODO: why is this code different from db_marks->MdidNotFinish?
            x.save()
            log.info(
                "Reset user {} question-annotation task {}".format(uname, x.group.gid)
            )
