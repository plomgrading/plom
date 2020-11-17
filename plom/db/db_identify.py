# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

from datetime import datetime
import logging

import peewee as pw

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName
from plom.db.tables import *


log = logging.getLogger("DB")


# ------------------
# Identifier stuff
# The ID-able tasks have group_type ="i", group.scanned=True,
# The todo id-tasks are IDGroup.status="todo"
# the done id-tasks have IDGroup.status="done"


def IDcountAll(self):
    """Count all tests in which ID pages are scanned."""
    try:
        return (
            Group.select()
            .where(
                Group.group_type == "i",
                Group.scanned == True,
            )
            .count()
        )
    except Group.DoesNotExist:
        return 0


def IDcountIdentified(self):
    """Count all tests in which ID pages are scanned and student has been identified."""
    try:
        return (
            IDGroup.select()
            .join(Group)
            .where(
                Group.scanned == True,
                IDGroup.identified == True,
            )
            .count()
        )
    except IDGroup.DoesNotExist:
        return 0


def IDgetNextTask(self):
    """Find unid'd test and send test_number to client"""
    with plomdb.atomic():
        try:  # grab the IDData reference provided not IDd but has been scanned
            iref = (
                IDGroup.select()
                .join(Group)
                .where(
                    IDGroup.status == "todo",
                    Group.scanned == True,
                )
                .get()
            )
            # note - test need not be all scanned, just the ID pages.
        except IDGroup.DoesNotExist:
            log.info("Nothing left on ID to-do pile")
            return None

        log.debug("Next ID task = {}".format(iref.test.test_number))
        return iref.test.test_number


def IDgiveTaskToClient(self, user_name, test_number):
    """Assign test #test_number as a task to the given user. Provided that task has not already been taken by another user, we return [True, image-list]."""
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.
    with plomdb.atomic():
        # get that test
        tref = Test.get_or_none(Test.test_number == test_number)
        if (
            tref is None
        ):  # should not happen - user should not be asking for nonexistant tests
            log.info("ID task - That test number {} not known".format(test_number))
            return [False]
        # grab the ID group of that test
        iref = tref.idgroups[0]
        # verify the id-group has been scanned - it should be if we got here.
        if iref.group.scanned == False:
            return [False]
        if not (iref.user is None or iref.user == uref):
            # has been claimed by someone else.
            return [False]
        # update status, owner of task, time
        iref.status = "out"
        iref.user = uref
        iref.time = datetime.now()
        iref.save()
        # update user activity
        uref.last_action = "Took ID task {}".format(test_number)
        uref.last_activity = datetime.now()
        uref.save()
        # return [true, page1, page2, etc]
        rval = [True]
        for p in iref.idpages.order_by(IDPage.order):
            rval.append(p.image.file_name)

        log.debug("Giving ID task {} to user {}".format(test_number, user_name))
        return rval


def IDgetDoneTasks(self, user_name):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list."""
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.

    query = IDGroup.select().where(IDGroup.user == uref, IDGroup.status == "done")
    idList = []
    for iref in query:
        idList.append([iref.test.test_number, iref.student_id, iref.student_name])
    log.debug("Sending completed ID tasks to user {}".format(user_name))
    return idList


def IDgetImage(self, user_name, test_number):
    """Return ID page images (+ Lpages) of test #test_number to user."""
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "NoTest"]
    # grab the IDData
    iref = tref.idgroups[0]
    # check corresponding group is scanned
    if iref.group.scanned is False:
        return [False, "NoScan"]
    # quick sanity check to make sure task given to user, (or if manager making request)
    if iref.user != uref and user_name != "manager":
        return [False, "NotOwner"]
    rval = [True]
    for p in iref.idpages.order_by(IDPage.order):
        rval.append(p.image.file_name)
    log.debug("Sending IDpages of test {} to user {}".format(test_number, user_name))
    return rval


def IDgetImageByNumber(self, image_number):
    """
    For every test, find the imageNumber'th page in the ID Pages and return the corresponding image filename. So gives returns a dictionary of testNumber -> filename.
    """
    rval = {}
    query = IDGroup.select()
    for iref in query:
        # for each iref, check that it is scanned and then grab page.
        gref = iref.group
        if not gref.scanned:
            continue
        # make a list of all the pages in the IDgroup
        pages = []
        for p in iref.idpages:
            pages.append(p.image.file_name)
        # grab the relevant page if it is in the list
        if len(pages) > image_number:
            rval[iref.test.test_number] = pages[image_number]
        # otherwise we don't add that test to the dictionary.
    return rval


def IDdidNotFinish(self, user_name, test_number):
    """When user logs off, any images they have still out should be put
    back on todo pile
    """
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.

    # Log user returning given tgv.
    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == test_number)
        if tref is None:
            log.info("That test number {} not known".format(test_number))
            return False

        iref = tref.idgroups[0]
        # sanity check that user has task out.
        if iref.user != uref or iref.status != "out":
            return False
        # update status, id-time. If out, then student name/number are not set.
        iref.status = "todo"
        iref.user = None
        iref.time = datetime.now()
        iref.identified = False
        iref.save()
        tref.identified = False
        tref.save()
        log.info("User {} did not ID task {}".format(user_name, test_number))


def ID_id_paper(self, paper_num, user_name, sid, sname, checks=True):
    """Associate student name and id with a paper in the database.

    See also :func:`plom.db.db_create.id_paper` which is just this with
    `checks=False`.

    Args:
        paper_num (int)
        user_name (str): User who did the IDing.
        sid (str, None): student ID.  `None` if the ID page was blank:
            typically `sname` will then contain some short explanation.
        sname (str): student name.
        checks (bool): by default (True), the paper must be scanned
            and the `username` must match the current owner of the
            paper (typically because the paper was assigned to them).
            You can pass False if its ID the paper without being
            owner (e.g., during automated IDing of prenamed papers.)

    Returns:
        tuple: `(True, None, None)` if succesful, `(False, 409, msg)`
            means `sid` is in use elsewhere, a serious problem for
            the caller to deal with.  `(False, int, msg)` covers all
            other errors.  `msg` gives details about errors.  Some
            of these should not occur, and indicate possible bugs.
            `int` gives a hint of suggested HTTP status code,
            currently it can be 404, 403, or 409.

    TODO: perhaps several sorts of exceptions would be better.
    """
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.

    logbase = 'User "{}" tried to ID paper {}'.format(user_name, paper_num)
    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == paper_num)
        if tref is None:
            msg = "denied b/c paper not found"
            log.error("{}: {}".format(logbase, msg))
            return False, 404, msg
        iref = tref.idgroups[0]
        if checks and iref.group.scanned == False:
            msg = "denied b/c its not scanned yet"
            log.error("{}: {}".format(logbase, msg))
            return False, 404, msg
        if checks and iref.user != uref:
            msg = 'denied b/c it belongs to user "{}"'.format(iref.user)
            log.error("{}: {}".format(logbase, msg))
            return False, 403, msg
        iref.user = uref
        iref.status = "done"
        iref.student_id = sid
        iref.student_name = sname
        iref.identified = True
        iref.time = datetime.now()
        try:
            iref.save()
        except pw.IntegrityError:
            msg = "student id {} already entered elsewhere".format(censorID(sid))
            log.error("{} but {}".format(logbase, msg))
            return False, 409, msg
        tref.identified = True
        tref.save()
        # update user activity
        uref.last_action = "Returned ID task {}".format(paper_num)
        uref.last_activity = datetime.now()
        uref.save()
        if sid:
            log.info(
                'Paper {} ID\'d by "{}" as "{}" "{}"'.format(
                    paper_num, user_name, censorID(sid), censorName(sname)
                )
            )
        else:
            log.info(
                'Paper {} ID\'d by "{}" as "{}" "{}"'.format(
                    paper_num, user_name, sid, sname
                )
            )
    return True, None, None


def IDgetImageFromATest(self):
    """Returns ID images from the first unid'd test."""
    query = (  # look for scanned ID groups which are not IDd yet.
        IDGroup.select()
        .join(Group)
        .where(
            Group.group_type == "i",
            Group.scanned == True,
            IDGroup.identified == False,
        )
        .limit(1)  # we only need 1.
    )
    if query.count() == 0:
        log.info("No unIDd IDPages to sennd to manager")
        return [False]
    log.info("Sending first unIDd IDPages to manager")

    iref = query[0]
    rval = [True]
    for p in iref.idpages.order_by(IDPage.order):
        rval.append(p.image.file_name)

    return rval


def IDreviewID(self, test_number):
    """Replace the owner of the ID task for test test_number, with the reviewer."""
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    iref = IDGroup.get_or_none(
        IDGroup.test == tref,
        IDGroup.identified == True,
    )
    if iref is None:
        return [False]
    with plomdb.atomic():
        iref.user = revref
        iref.time = datetime.now()
        iref.save()
    log.info("ID task {} set for review".format(test_number))
    return [True]
