# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from datetime import datetime
import logging

import peewee as pw

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName
from plom.db.tables import plomdb
from plom.db.tables import DNMPage, Group, IDGroup, Test, User


log = logging.getLogger("DB")


# ------------------
# Identifier stuff
# The ID-able tasks have group_type ="i", group.scanned=True,
# The todo id-tasks are IDGroup.status="todo"
# the done id-tasks have IDGroup.status="done"


def IDcountAll(self):
    """Count all tests in which the ID page is scanned."""
    try:
        return (
            Group.select()
            .where(
                Group.group_type == "i",
                Group.scanned == True,  # noqa: E712
            )
            .count()
        )
    except pw.DoesNotExist:
        return 0


def IDcountIdentified(self):
    """Count all tests in which the ID page is scanned and student has been identified."""
    try:
        return (
            IDGroup.select()
            .join(Group)
            .where(
                Group.scanned == True,  # noqa: E712
                IDGroup.identified == True,  # noqa: E712
            )
            .count()
        )
    except pw.DoesNotExist:
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
                    Group.scanned == True,  # noqa: E712
                )
                .get()
            )
            # as per #1811 - the user should be none here - assert here.
            assert (
                iref.user is None
            ), f"ID-Task for test {iref.test.test_number} is todo, but has a user = {iref.user.name}"
            # note - test need not be all scanned, just the ID page.
        except pw.DoesNotExist:
            log.info("Nothing left on ID to-do pile")
            return None

        log.debug("Next ID task = {}".format(iref.test.test_number))
        return iref.test.test_number


def IDgiveTaskToClient(self, user_name, test_number):
    """Assign test #test_number as a task to the given user if available.

    Returns:
        2-tuple: (True, image_file) if available else (False, msg) where
             msg is a short message: "NoTest", "NotScanned", "NotOwner".
    """
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.
    with plomdb.atomic():
        # get that test
        tref = Test.get_or_none(Test.test_number == test_number)
        if tref is None:
            log.info("ID task - test number %s not known", test_number)
            return (False, "NoTest")
        # grab the ID group of that test
        iref = tref.idgroups[0]
        # verify the id-group has been scanned - it should be if we got here.
        if not iref.group.scanned:
            return (False, "NotScanned")
        if not (iref.user is None or iref.user == uref):
            # has been claimed by someone else.
            # see also #1811 - if a task is "todo" then its user should be None.
            return (False, "NotOwner")
        # update status, owner of task, time
        iref.status = "out"
        iref.user = uref
        iref.time = datetime.now()
        iref.save()
        # update user activity
        uref.last_action = "Took ID task {}".format(test_number)
        uref.last_activity = datetime.now()
        uref.save()
        log.debug("Giving ID task {} to user {}".format(test_number, user_name))
        return (True, iref.idpages[0].image.file_name)


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
    """Return ID page image of a paper.

    args:
        user_name (str)
        test_number (int)

    Returns:
        2-tuple: `(True, file)` or `(True, None)``. Otherwise, `(False, "NoTest")` or `(False, "NoScanAndNotIDd")` or `(False, "NotOwner")`.
    """
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "NoTest")
    # grab the IDData
    iref = tref.idgroups[0]
    # Now check corresponding group has been scanned.
    # Note that if the group is unscanned, and the test has not
    # been identified then we have a problem.
    # However, if the test has been identified, but ID group unscanned,
    # then this is okay (fixes #1629).
    # This is precisely what will happen when using plom for homework, there
    # are no id-page (so idgroup is unscanned), but the system automagically
    # identifies the test.
    if (not iref.group.scanned) and (not tref.identified):
        return (False, "NoScanAndNotIDd")
    # quick sanity check to make sure task given to user, (or if manager making request)
    if iref.user != uref and user_name != "manager":
        return (False, "NotOwner")
    log.debug("Sending IDpage of test {} to user {}".format(test_number, user_name))
    if len(iref.idpages) == 0:
        return (True, None)
    else:
        return (True, iref.idpages[0].image.file_name)


def ID_get_donotmark_images(self, test_number):
    """Return the DoNotMark page images of a paper.

    args:
        test_number (int)

    Returns:
        2-tuple: `(True, file_list)` where `file_list` is a possibly-empty
            list of file names.  Otherwise, `(False, "NoTest")` or
            `(False, "NoScanAndNotIDd")`.
    """
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "NoTest")
    iref = tref.dnmgroups[0]
    # Now check corresponding group has been scanned.
    # Note that if the group is unscanned, and the test has not
    # been identified then we have a problem.
    # However, if the test has been identified, but DNM group unscanned,
    # then this is okay (fixes #1629).
    # This is precisely what will happen when using plom for homework, there
    # are no dnm-pages (so dnmgroup is unscanned), but the system automagically
    # identifies the test.
    if (not iref.group.scanned) and (not tref.identified):
        return (False, "NoScanAndNotIDd")
    file_list = []
    for p in iref.dnmpages.order_by(DNMPage.order):
        file_list.append(p.image.file_name)
    log.debug(f"Sending DNMpages of test {test_number}")
    return (True, file_list)


def IDgetImagesOfNotAutoIdentified(self):
    """
    For every non-auto'd test, find the filename of its idpage. So gives returns a dictionary of testNumber -> filename.
    """
    rval = {}
    uref = User.get(User.name == "HAL")
    query = Group.select().where(
        Group.group_type == "i", Group.scanned == True  # noqa: E712
    )
    for gref in query:
        iref = gref.idgroups[0]  # there is always exactly 1.
        # we want to ignore pre-named papers - those are owned by HAL
        # can improve this query.
        if iref.user == uref:
            continue
        # grab the relevant page if it is there
        if len(iref.idpages) == 0:
            # otherwise we don't add that test to the dictionary.
            continue
        else:
            rval[iref.test.test_number] = iref.idpages[0].image.file_name
    return rval


def ID_id_paper(self, paper_num, user_name, sid, sname, checks=True):
    """Associate student name and id with a paper in the database.

    Used by the normal users for identifying papers.

    See also :func:`plom.db.db_create.id_paper` which is just this with
    `checks=False`, and is used by manager.  Likely want to consolidate.

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
        tuple: `(True, None, None)` if successful or `(False, int, msg)`
        on errors, where `msg` gives details about the error.  Some of
        of these should not occur, and indicate possible bugs.  `int`
        gives a hint of suggested HTTP status code, currently it can be
        404, 403, or 409.
        (False, 403, msg) for ID tasks belongs to a different user,
        only tested for when ``checks=True``.
        (False, 404, msg) for paper not found or not scanned yet.
        (False, 409, msg) means `sid` is in use elsewhere.
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
        if checks and (not iref.group.scanned):
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
            log.error(f"{logbase} but student id {censorID(sid)} in use elsewhere")
            return False, 409, f"student id {sid} in use elsewhere"
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
    """Returns ID image from a randomly selected unid'd test."""
    query = (  # look for scanned ID groups which are not IDd yet.
        IDGroup.select()
        .join(Group)
        .where(
            Group.group_type == "i",
            Group.scanned == True,  # noqa: E712
            IDGroup.identified == False,  # noqa: E712
        )
        .order_by(pw.fn.Random())
        .limit(1)  # we only need 1.
    )
    if query.count() == 0:
        log.info("No unIDd IDPage to send to manager")
        return [False]
    log.info("Sending random unIDd IDPage to manager")

    iref = query[0]
    return [True, iref.idpages[0].image.file_name]


def IDreviewID(self, test_number):
    """Replace the owner of the ID task for test test_number, with the reviewer."""
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    iref = IDGroup.get_or_none(
        IDGroup.test == tref,
        IDGroup.identified == True,  # noqa: E712
    )
    if iref is None:
        return [False]
    with plomdb.atomic():
        iref.user = revref
        iref.time = datetime.now()
        iref.save()
    log.info("ID task {} set for review".format(test_number))
    return [True]
