# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from datetime import datetime, timezone
import logging

import peewee as pw

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName
from plom.db.tables import DNMPage, Group, IDGroup, IDPrediction, Test, User


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


def IDgetIdentifiedTests(self):
    """All tests in which the ID page is scanned and student has been identified."""
    try:
        stuff = (
            IDGroup.select()
            .join(Group)
            .where(
                Group.scanned == True,  # noqa: E712
                IDGroup.identified == True,  # noqa: E712
            )
        )
    except pw.DoesNotExist:
        stuff = []
    return [(x.test.test_number, x.student_id, x.student_name) for x in stuff]


def IDgetUnidentifiedTests(self):
    """All tests in which the ID page is scanned but the student is not yet identified."""
    try:
        stuff = (
            IDGroup.select()
            .join(Group)
            .where(
                Group.scanned == True,  # noqa: E712
                IDGroup.identified == False,  # noqa: E712
            )
        )
    except pw.DoesNotExist:
        stuff = []
    return [x.test.test_number for x in stuff]


def IDgetNextTask(self):
    """Find unid'd test and send test_number to client"""

    # priority given to tests without prediction
    # then tests with prediction - low certainty before high certainty.

    with self._db.atomic():
        # Filter tests that have IDGroup.status = todo and Group.scanned=True.
        # get tests whose id groups are on the todo pile
        unidentified_tests = Test.select().join(IDGroup).where(IDGroup.status == "todo")
        # now make sure they are all scanned.
        unidentified_tests = unidentified_tests.join(Group).where(
            Group.scanned == True  # noqa: E712
        )
        # Now refine this to get tests with no IDPrediction.
        # so join the IDpred table (outer join to get things even when test-link - then we can test on that field being null)
        no_prediction = (
            unidentified_tests.switch(Test)
            .join(IDPrediction, pw.JOIN.LEFT_OUTER)
            .where(IDPrediction.test.is_null())
        )
        try:
            tref = no_prediction.get()
            log.info(
                f"ID-task {tref.test_number} has no prediction and is todo - telling client"
            )
            # got one!
        except pw.DoesNotExist:
            # all tests id'd or have a prediction
            # so grab un-id'd test with lowest certainty
            with_prediction = (
                unidentified_tests.switch(Test)
                .join(IDPrediction)
                .order_by(IDPrediction.certainty)
            )
            try:
                tref = with_prediction.get()
                log.info(
                    f"ID-task {tref.test_number} has prediction with certainty {tref.idpredictions[0].certainty} and is todo - telling client"
                )
                # got one!
            except pw.DoesNotExist:
                # all jobs must be done.
                log.info("Nothing left on ID to-do pile")
                return None
        # get the idgroup associated to the test
        iref = tref.idgroups[0]
        # as per #1811 - the user should be none here
        assert (
            iref.user is None
        ), f"ID-Task for test {tref.test_number} is todo, but has a user = {iref.user.name}"
        # note - test need not be all scanned, just the ID page.
        return tref.test_number


def IDgiveTaskToClient(self, user_name, test_number):
    """Assign test #test_number as a task to the given user if available.

    Returns:
        2-tuple: `(True, image_file)` if available else `(False, msg)`
        where `msg` is a short string: "NoTest", "NotScanned", "NotOwner".
    """
    uref = User.get(name=user_name)
    # since user authenticated, this will always return legit ref.
    with self._db.atomic():
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
        iref.time = datetime.now(timezone.utc)
        iref.save()
        # update user activity
        uref.last_action = "Took ID task {}".format(test_number)
        uref.last_activity = datetime.now(timezone.utc)
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


def IDgetImagesOfUnidentified(self):
    """
    For every used but un-identified test, find the filename of its idpage. So gives returns a dictionary of testNumber -> filename.

    TODO: add an optional flag to drop those with high (prenamed) level of
    prediction confidence?
    """
    rval = {}
    query = Group.select().where(
        Group.group_type == "i", Group.scanned == True  # noqa: E712
    )
    for gref in query:
        iref = gref.idgroups[0]  # there is always exactly 1.
        # grab the relevant page if it is there
        if len(iref.idpages) == 0:
            # otherwise we don't add that test to the dictionary.
            continue
        else:
            rval[iref.test.test_number] = iref.idpages[0].image.file_name
    return rval


def ID_id_paper(self, paper_num, user_name, sid, sname, checks=True):
    """Associate student name and id with a paper in the database.

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
    with self._db.atomic():
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
        iref.time = datetime.now(timezone.utc)
        try:
            iref.save()
        except pw.IntegrityError as e:
            log.error(f"{logbase}: {e}; determining where sid %s used", censorID(sid))
            other = IDGroup.get_or_none(IDGroup.student_id == sid)
            if other is None:
                msg = f"student id {sid} in use but we don't know where!"
                msg += " This is unexpected - please report an issue"
                logmsg = "student id %s in use but we don't know where!"
                logmsg += " This is unexpected - please report an issue"
            else:
                msg = f"student id {sid} in use in paper {other.test.test_number:04}"
                logmsg = f"student id %s in use in paper {other.test.test_number}"
            log.error(f"{logbase}: {logmsg}", censorID(sid))
            return False, 409, msg
        tref.identified = True
        tref.save()

        # TODO - decide if it is better to simply update the predictions
        # with something like certainty 0.99 and predictor = "human"

        # Issue #2081: for now, and maybe forever, we do not clear predictions
        # upon ID.  I think that is correct: callers can adjust their predictions
        # if desired.
        # # remove any predictions associated with this test_number
        # for preidref in tref.idpredictions:
        #     preidref.delete_instance()
        # # remove any predictions associated with the student id
        # for preidref in IDPrediction.select().where(
        #     IDPrediction.student_id == sid
        # ):  # noqa: E712
        #     preidref.delete_instance()

        # update user activity
        uref.last_action = "Returned ID task {}".format(paper_num)
        uref.last_activity = datetime.now(timezone.utc)
        uref.save()
        log.info(
            'Paper {} ID\'d by "{}" as "{}" "{}"'.format(
                paper_num, user_name, censorID(sid), censorName(sname)
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
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return False
    iref = IDGroup.get_or_none(
        IDGroup.test == tref,
        IDGroup.identified == True,  # noqa: E712
    )
    if iref is None:
        return False
    with self._db.atomic():
        iref.user = revref
        iref.time = datetime.now(timezone.utc)
        iref.save()
    log.info("ID task %s set for review", test_number)
    return True


def ID_get_predictions(self, *, predictor=None):
    """Return a dict of predicted test to student_ids.
       If all predictions are returned, each dict value contains a list of prediction dicts.
       If predictions for a specified predictor are returned, each dict value contains a single prediction dict.

    Keyword Args:
        predictor (str/None): which predictor.  If not specified,
            defaults to `None` which means all predictors, so multiple
            predictions may be returned for each paper number.
    """
    predictions = {}
    if predictor:
        log.info('querying for predictions from "%s"', predictor)
        query = IDPrediction.select().where(IDPrediction.predictor == predictor)
        for preidref in query:
            predictions[preidref.test.test_number] = {
                "student_id": preidref.student_id,
                "certainty": preidref.certainty,
                "predictor": preidref.predictor,
            }
    else:
        query = IDPrediction.select()
        for preidref in query:
            if predictions.get(preidref.test.test_number) is None:
                predictions[preidref.test.test_number] = []
            predictions[preidref.test.test_number].append(
                {
                    "student_id": preidref.student_id,
                    "certainty": preidref.certainty,
                    "predictor": preidref.predictor,
                }
            )
    return predictions


def ID_delete_predictions(self, *, predictor=None):
    """Remove the predictions for IDs, either from a particular predictor or all of them.

    Keyword Args:
        predictor (str/None): which predictor.  If not specified,
            defaults to `None` which means all predictors.
    """
    if predictor:
        log.info('deleting all predictions from "%s"', predictor)
        query = IDPrediction.select().where(IDPrediction.predictor == predictor)
    else:
        log.info("deleting all predictions from all predictors")
        query = IDPrediction.select()
    for preidref in query:
        preidref.delete_instance()
