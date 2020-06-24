from plom.db.tables import plomdb, User, Test, TPage, SumData
from datetime import datetime

import logging

log = logging.getLogger("DB")


def TcountAll(self):
    """Count all scanned tests - each is (potentially) a task that needs doing.
    """
    try:
        return Test.select().where(Test.scanned == True).count()
    except Test.DoesNotExist:
        return 0


def TcountTotalled(self):
    """Count all scanned tests that have also been summed.
    """
    try:
        return Test.select().where(Test.totalled == True, Test.scanned == True,).count()
    except Test.DoesNotExist:
        return 0


def TgetNextTask(self):
    """Find the next un-summed test and return the corresponding test_number to client
    """
    with plomdb.atomic():
        try:
            sref = (
                SumData.select()
                .join(Test)
                .where(SumData.status == "todo", Test.scanned == True)
                .get()
            )
        except SumData.DoesNotExist:
            log.info("Nothing left on totaller to-do pile")
            return None

        log.debug("Next Totalling task = {}".format(sref.test.test_number))
        return sref.test.test_number


def TgetDoneTasks(self, user_name):
    """When a totaller-client logs on they request a list of papers they have already summed.
    Return a list of [test_number, and sum_mark].
    """
    uref = User.get(name=user_name)  # authenticated, so not-None
    query = SumData.select().where(SumData.user == uref, SumData.status == "done")
    tList = []
    for sref in query:
        tList.append([sref.test.test_number, sref.sum_mark])
    log.debug("Sending completed totalling tasks to {}".format(user_name))
    return tList


def TgiveTaskToClient(self, user_name, test_number):
    """Assign test #test_number as a task to the given user. Provided that task has not already been taken by another user, we return [True, image] where image = the file_name of the very first test_page in the paper. This does not work with either loose pages or homework pages.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None
    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == test_number)
        # user should not be asking for a non-existant test, so this should not happen
        if tref is None:
            log.warning(
                "Cannot give totalling task {} to {} - task not known".format(
                    test_number, user_name
                )
            )
            return [False]
        # cannot give an unscanned test. This should not happen.
        elif tref.scanned == False:
            return [False]

        # grab the sumdata of that test
        sref = tref.sumdata[0]
        if (sref.user is not None) and (sref.user != uref):
            # has been claimed by someone else.
            return [False]
        # update status, user and time.
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
        log.info("Giving totalling task {} to user {}".format(test_number, user_name))
        return rval


def TdidNotFinish(self, user_name, test_number):
    """When user logs off, any tasks they have still out should be put
    back on todo pile. No returned objects.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None
    # Log user returning given test_number.

    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == test_number)
        if tref is None:
            log.error("TdidNotFinish - test number {} not known".format(test_number))
            return
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
        log.info("User {} did not total task {}".format(user_name, test_number))


def TgetImage(self, user_name, test_number):
    """Pass the image filename of the front testpage of the given test to the given user - if they own the associated task or they are manager.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref.scanned == False:  # this should not happen.
        return [False]
    sref = tref.sumdata[0]
    # check if task given to user or user=manager
    if sref.user != uref and user_name != "manager":
        return [False]
    # grab the front page of the test
    pref = TPage.get(TPage.test == tref, TPage.page_number == 1)
    log.info(
        "Sending cover-page of test {} to user {} = {}".format(
            test_number, user_name, pref.image.file_name
        )
    )
    return [True, pref.image.file_name]


def TtakeTaskFromClient(self, test_number, user_name, totalMark):
    """Take task #test_number back from given user with the associated total.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None

    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == test_number)
        if tref is None:  # client should not be returning non-existent test
            log.error(
                "TtakeTaskFromClient - test number {} not known".format(test_number)
            )
            return [False]
        if tref.scanned == False:  # this should not happen either
            return [False]
        # grab the associated sumdata
        sref = tref.sumdata[0]
        if sref.user != uref:
            # that belongs to someone else - this is a serious error
            log.error(
                'User "{}" returned totalled-task {} that belongs to "{}"'.format(
                    user_name, test_number, sref.user.name
                )
            )
            return [False]
        # update status, time, mark.
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
                user_name, test_number, totalMark
            )
        )
        return [True]


def TreviewTotal(self, test_number):
    """Replace the owner of the Totalling task for test test_number, with the reviewer.
    """
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    sref = tref.sumdata[0]  # grab the sumdata object
    if sref.summed is False:  # check it has actually been summed.
        return [False]
    with plomdb.atomic():
        sref.user = revref
        sref.time = datetime.now()
        sref.save()
    log.info("Totalling task {} set for review".format(test_number))
    return [True]
