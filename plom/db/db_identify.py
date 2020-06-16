from plom.db.tables import *
from datetime import datetime
import peewee as pw
from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

import logging

log = logging.getLogger("DB")

# ------------------
# Identifier stuff
# The ID-able tasks have group_type ="i", group.scanned=True,
# The todo id-tasks are IDGroup.status="todo"
# the done id-tasks have IDGroup.status="done"


def IDcountAll(self):
    """Count all the records"""
    try:
        return (
            Group.select()
            .where(Group.group_type == "i", Group.scanned == True,)
            .count()
        )
    except Group.DoesNotExist:
        return 0


def IDcountIdentified(self):
    """Count all the ID'd records"""
    try:
        return (
            IDGroup.select()
            .join(Group)
            .where(Group.scanned == True, IDGroup.identified == True,)
            .count()
        )
    except IDGroup.DoesNotExist:
        return 0


def IDgetNextTask(self):
    """Find unid'd test and send test_number to client"""
    with plomdb.atomic():
        try:
            x = (
                IDGroup.select()
                .join(Group)
                .where(IDGroup.status == "todo", Group.scanned == True,)
                .get()
            )
        except IDGroup.DoesNotExist:
            log.info("Nothing left on ID to-do pile")
            return None

        log.debug("Next ID task = {}".format(x.test.test_number))
        return x.test.test_number


def IDgiveTaskToClient(self, uname, test_number):
    uref = User.get(name=uname)
    # since user authenticated, this will always return legit ref.

    try:
        with plomdb.atomic():
            tref = Test.get_or_none(Test.test_number == test_number)
            if tref is None:
                return [False]
            iref = tref.idgroups[0]
            # verify the id-group has been scanned - it should always be scanned.if we get here.
            if iref.group.scanned == False:
                return [False]
            if iref.user is not None and iref.user != uref:
                # has been claimed by someone else.
                return [False]
            # update status, Student-number, name, id-time.
            iref.status = "out"
            iref.user = uref
            iref.time = datetime.now()
            iref.save()
            # update user activity
            uref.last_action = "Took ID task {}".format(test_number)
            uref.last_activity = datetime.now()
            uref.save()
            # return [true, page1, page2, etc]
            gref = iref.group
            rval = [True]
            for p in gref.tpages.order_by(TPage.page_number):  # give TPages
                rval.append(p.image.file_name)
            for p in gref.hwpages.order_by(HWPage.order):  # then give HWPages
                rval.append(p.image.file_name)
            log.debug("Giving ID task {} to user {}".format(test_number, uname))
            return rval

    except Test.DoesNotExist:
        log.info("ID task - That test number {} not known".format(test_number))
        return False


def IDgetDoneTasks(self, uname):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list."""
    uref = User.get(name=uname)
    # since user authenticated, this will always return legit ref.

    query = IDGroup.select().where(IDGroup.user == uref, IDGroup.status == "done")
    idList = []
    for x in query:
        idList.append([x.test.test_number, x.status, x.student_id, x.student_name])
    log.debug("Sending completed ID tasks to user {}".format(uname))
    return idList


def IDgetImage(self, uname, t):
    uref = User.get(name=uname)
    # since user authenticated, this will always return legit ref.

    tref = Test.get_or_none(Test.test_number == t)
    if tref.scanned == False:
        return [False]
    iref = tref.idgroups[0]
    # quick sanity check to make sure task given to user, (or if manager making request)
    if iref.user == uref or uname == "manager":
        pass
    else:
        return [False]
    # gref = iref.group
    rval = [True]
    for p in iref.idpages.order_by(IDPage.order):
        rval.append(p.image.file_name)
    # for p in gref.tpages.order_by(TPage.page_number):  # give TPages
    #     rval.append(p.image.file_name)
    # for p in gref.hwpages.order_by(HWPage.order):  # then give HWPages
    #     rval.append(p.image.file_name)
    log.debug("Sending IDpages of test {} to user {}".format(t, uname))
    return rval


def IDgetImageList(self, imageNumber):
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
        # for p in gref.tpages.order_by(TPage.page_number):
        # pages.append(p.file_name)
        # for p in gref.hwpages.order_by(HWPage.order):  # then give HWPages
        # rval.append(p.image.file_name)
        # grab the relevant page if there.
        if len(pages) > imageNumber:
            rval[iref.test.test_number] = pages[imageNumber]
    return rval


def IDdidNotFinish(self, uname, test_number):
    """When user logs off, any images they have still out should be put
    back on todo pile
    """
    uref = User.get(name=uname)
    # since user authenticated, this will always return legit ref.

    # Log user returning given tgv.
    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == test_number)
        if tref is None:
            log.info("That test number {} not known".format(test_number))
            return False

        if tref.scanned == False:
            return
        iref = tref.idgroups[0]
        # sanity check that user has task
        if iref.user == uref and iref.status == "out":
            pass
        else:  # someone else has it, or it is not out.
            return
        # update status, Student-number, name, id-time.
        iref.status = "todo"
        iref.user = None
        iref.time = datetime.now()
        iref.identified = False
        iref.save()
        tref.identified = False
        tref.save()
        log.info("User {} did not ID task {}".format(uname, test_number))


def IDtakeTaskFromClient(self, test_number, uname, sid, sname):
    """Get ID'dimage back from client - update record in database."""
    uref = User.get(name=uname)
    # since user authenticated, this will always return legit ref.

    try:
        with plomdb.atomic():
            tref = Test.get_or_none(Test.test_number == test_number)
            if tref is None:
                return [False, False]
            iref = tref.idgroups[0]
            # verify the id-group has been scanned - it should always be scanned.if we get here.
            if iref.group.scanned == False:
                return [False, False]

            if iref.user != uref:
                # that belongs to someone else - this is a serious error
                return [False, False]
            # update status, Student-number, name, id-time.
            iref.status = "done"
            iref.student_id = sid
            iref.student_name = sname
            iref.identified = True
            iref.time = datetime.now()
            iref.save()
            tref.identified = True
            tref.save()
            # update user activity
            uref.last_action = "Returned ID task {}".format(test_number)
            uref.last_activity = datetime.now()
            uref.save()
            return [True]
            log.info(
                'User "{}" returning ID-task "{}" with "{}" "{}"'.format(
                    uname, test_number, censorID(sid), censorName(sname)
                )
            )
    except IDGroup.DoesNotExist:
        log.error("ID take task - That test number {} not known".format(test_number))
        return [False, False]
    except pw.IntegrityError:
        log.error(
            "ID take task - Student number {} already entered".format(censorID(sid))
        )
        return [False, True]


def IDgetRandomImage(self):
    # TODO - make random image rather than 1st
    query = (
        Group.select()
        .join(IDGroup)
        .where(
            Group.group_type == "i", Group.scanned == True, IDGroup.identified == False,
        )
        .limit(1)
    )
    if query.count() == 0:
        log.info("No unIDd IDPages to sennd to manager")
        return [False]
    log.info("Sending first unIDd IDPages to manager")
    gref = query[0]
    rval = [True]
    for p in gref.tpages.order_by(TPage.page_number):
        rval.append(p.image.file_name)
    for p in gref.hwpages.order_by(HWPage.order):  # then give HWPages
        rval.append(p.image.file_name)
    return rval


def IDreviewID(self, test_number):
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    iref = IDGroup.get_or_none(IDGroup.test == tref, IDGroup.identified == True,)
    if iref is None:
        return [False]
    with plomdb.atomic():
        iref.user = revref
        iref.time = datetime.now()
        iref.save()
    log.info("ID task {} set for review".format(test_number))
    return [True]
