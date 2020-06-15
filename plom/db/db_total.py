from plom.db.tables import plomdb, User, Test, TPage, SumData
from datetime import datetime

import logging

log = logging.getLogger("DB")


def TcountAll(self):
    """Count all the records"""
    try:
        return Test.select().where(Test.scanned == True).count()
    except Test.DoesNotExist:
        return 0


def TcountTotalled(self):
    """Count all the records"""
    try:
        return Test.select().where(Test.totalled == True, Test.scanned == True,).count()
    except Test.DoesNotExist:
        return 0


def TgetNextTask(self):
    """Find unid'd test and send test_number to client"""
    with plomdb.atomic():
        try:
            x = (
                SumData.select()
                .join(Test)
                .where(SumData.status == "todo", Test.scanned == True)
                .get()
            )
        except SumData.DoesNotExist:
            log.info("Nothing left on totaller to-do pile")
            return None

        log.debug("Next Totalling task = {}".format(x.test.test_number))
        return x.test.test_number


def TgetDoneTasks(self, uname):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list."""
    uref = User.get(name=uname)  # authenticated, so not-None
    query = SumData.select().where(SumData.user == uref, SumData.status == "done")
    tList = []
    for x in query:
        tList.append([x.test.test_number, x.status, x.sum_mark])
    log.debug("Sending completed totalling tasks to {}".format(uname))
    return tList


def TgiveTaskToClient(self, uname, test_number):
    uref = User.get(name=uname)  # authenticated, so not-None
    try:
        with plomdb.atomic():
            tref = Test.get_or_none(Test.test_number == test_number)
            if tref.scanned == False:
                return [False]
            sref = tref.sumdata[0]
            if sref.user is None or sref.user == uref:
                pass
            else:  # has been claimed by someone else.
                return [False]
            # update status, Student-number, name, id-time.
            sref.status = "out"
            sref.user = uref
            sref.time = datetime.now()
            sref.save()
            # update user activity
            uref.last_action = "Took T task {}".format(test_number)
            uref.last_activity = datetime.now()
            uref.save()
            # return [true, page1]
            pref = TPage.get(test=tref, page_number=1)
            return [True, pref.image.file_name]
            log.info("Giving totalling task {} to user {}".format(test_number, uname))
            return rval

    except Test.DoesNotExist:
        log.warning(
            "Cannot give totalling task {} to {} - task not known".format(
                test_number, uname
            )
        )
        return False


def TdidNotFinish(self, uname, test_number):
    """When user logs off, any images they have still out should be put
    back on todo pile
    """
    uref = User.get(name=uname)  # authenticated, so not-None
    # Log user returning given tgv.
    try:
        with plomdb.atomic():
            tref = Test.get_or_none(Test.test_number == test_number)
            if tref.scanned == False:
                return
            sref = tref.sumdata[0]
            if sref.user == uref and sref.status == "out":
                pass
            else:  # has been claimed by someone else.
                return
            # update status, Student-number, name, id-time.
            sref.status = "todo"
            sref.user = None
            sref.time = datetime.now()
            sref.summed = False
            sref.save()
            tref.summed = False
            tref.save()
            log.info("User {} did not total task {}".format(uname, test_number))
    except Test.DoesNotExist:
        log.error("TdidNotFinish - test number {} not known".format(test_number))
        return False


def TgetImage(self, uname, t):
    uref = User.get(name=uname)  # authenticated, so not-None
    tref = Test.get_or_none(Test.test_number == t)
    if tref.scanned == False:
        return [False]
    sref = tref.sumdata[0]
    # check if task given to user or user=manager
    if sref.user == uref or uname == "manager":
        pass
    else:
        return [False]
    pref = TPage.get(TPage.test == tref, TPage.page_number == 1)
    log.info(
        "Sending cover-page of test {} to user {} = {}".format(t, uname, pref.file_name)
    )
    return [True, pref.file_name]


def TtakeTaskFromClient(self, test_number, uname, totalMark):
    uref = User.get(name=uname)  # authenticated, so not-None

    try:
        with plomdb.atomic():
            tref = Test.get_or_none(Test.test_number == test_number)
            if tref.scanned == False:
                return [False]
            sref = tref.sumdata[0]
            if sref.user != uref:
                # that belongs to someone else - this is a serious error
                log.error(
                    'User "{}" returned totalled-task {} that belongs to "{}"'.format(
                        uname, test_number, sref.user.name
                    )
                )
                return [False]
            # update status, Student-number, name, id-time.
            sref.status = "done"
            sref.sum_mark = totalMark
            sref.summed = True
            sref.time = datetime.now()
            sref.save()
            tref.totalled = True
            tref.save()
            # update user activity
            uref.last_action = "Returned T task {}".format(test_number)
            uref.last_activity = datetime.now()
            uref.save()
            log.debug(
                "User {} returning totalled-task {} with {}".format(
                    uname, test_number, totalMark
                )
            )
            return [True]
    except Test.DoesNotExist:
        log.error("TtakeTaskFromClient - test number {} not known".format(test_number))
        return [False]
