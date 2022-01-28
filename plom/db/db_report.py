# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2021 Nicholas J H Lai

from collections import defaultdict
from datetime import datetime, timedelta
import logging

from plom.db.tables import Group, IDGroup, QGroup, Test, TPage, User


log = logging.getLogger("DB")


# ------------------
# Reporting functions


def RgetScannedTests(self):
    """Get a dict of all scanned tests indexed by test_number.
    Each test lists pairs [page-code, page-version].
    page-code is t{page}, h{question}{order}, or l{order}.
    """
    scan_dict = {}
    for tref in Test.select().where(Test.scanned == True):  # noqa: E712
        pScanned = []
        # first append test-pages
        for p in tref.tpages:
            if p.scanned is True:
                pScanned.append(["t.{}".format(p.page_number), p.version])
        # then append hw-pages in question-order
        for qref in tref.qgroups:
            gref = qref.group
            for p in gref.hwpages:
                pScanned.append(["h.{}.{}".format(qref.question, p.order), p.version])
        # then append extra-pages in question-order
        for qref in tref.qgroups:
            gref = qref.group
            for p in gref.expages:
                pScanned.append(["e.{}.{}".format(qref.question, p.order), p.version])
        scan_dict[tref.test_number] = pScanned
    log.debug("Sending list of scanned tests")
    return scan_dict


def RgetIncompleteTests(self):
    """Get dict of incomplete tests - ie some test pages scanned but not all.
    Indexed by test_number
    Each test lists triples [page-code, page-version, scanned_or_not].
    page-code is t{page}, h{question}{order}, or l{order}.
    Note - if no tpages scanned, then it will not return tpages.
    Similalry, if no hwpages/expages scanned, then it will not return hwpages/expages.
    """
    incomp_dict = {}
    for tref in Test.select().where(
        Test.scanned == False, Test.used == True  # noqa: E712
    ):
        page_state = []
        # if no tpages scanned then don't display
        if (
            TPage.select()
            .where(TPage.test == tref, TPage.scanned == True)  # noqa: E712
            .count()
            > 0
        ):
            for p in tref.tpages:
                page_state.append(["t.{}".format(p.page_number), p.version, p.scanned])

        # if no HW pages at all - then don't display.
        if tref.hwpages.count() > 0:
            # then append hw-pages in question-order
            for qref in tref.qgroups.order_by(QGroup.question):
                # if no HW pages scanned then display a hwpage 1 as unscanned.
                if qref.group.hwpages.count() == 0:
                    page_state.append(
                        ["h.{}.{}".format(qref.question, 1), qref.version, False]
                    )
                else:
                    for p in qref.group.hwpages:  # hw pages are always scanned
                        page_state.append(
                            ["h.{}.{}".format(qref.question, p.order), p.version, True]
                        )
        # if no ex pages at all - then don't display.
        if tref.expages.count() > 0:
            # then append ex-pages in question-order
            for qref in tref.qgroups.order_by(QGroup.question):
                for p in qref.group.expages:  # ex pages are always scanned
                    page_state.append(
                        ["e.{}.{}".format(qref.question, p.order), p.version, True]
                    )
        incomp_dict[tref.test_number] = page_state
    log.debug("Sending list of incomplete tests")
    return incomp_dict


def RgetDanglingPages(self):
    """Find all pages that belong to groups that are not scanned"""
    dangling = []
    # check all unscanned groups
    for gref in Group.select().where(Group.scanned == False):  # noqa: E712
        for pref in gref.tpages:
            if pref.scanned is True:
                dangling.append(
                    {
                        "test": gref.test.test_number,
                        "group": gref.gid,
                        "type": "tpage",
                        "page": pref.page_number,
                        "code": f"t.{pref.page_number}",
                    }
                )
        for pref in gref.hwpages:
            q = gref.qgroups[0].question
            dangling.append(
                {
                    "test": pref.test.test_number,
                    "group": gref.gid,
                    "type": "hwpage",
                    "order": pref.order,
                    "code": f"h.{q}.{pref.order}",
                }
            )
        for pref in gref.expages:
            q = gref.qgroups[0].question
            dangling.append(
                {
                    "test": pref.test.test_number,
                    "group": gref.gid,
                    "type": "expage",
                    "order": pref.order,
                    "code": f"e.{q}.{pref.order}",
                }
            )
    # return list sorted by test-number
    return sorted(dangling, key=lambda p: p["test"])


def RgetCompleteHW(self):
    """Get a list of [test_number, sid] that have complete hw-uploads - ie all questions present."""
    hw_complete = []
    # look at all the scanned tests - they will either be hwpages or tpages
    for tref in Test.select().where(Test.scanned == True):  # noqa: E712
        # make sure every group has hwpages
        qhwlist = [qref.group.hwpages.count() for qref in tref.qgroups]
        if 0 not in qhwlist:
            hw_complete.append([tref.test_number, tref.idgroups[0].student_id])
    return hw_complete


def RgetMissingHWQ(self):
    """Get dict of tests with missing HW Pages - ie some pages scanned but not all.
    Indexed by test_number
    Each test gives [sid, missing hwq's].
    The question-group of each hw-q is checked to see if any tpages present - if there are some, then it is not included. It is likely partially scanned.
    """
    incomp_dict = {}
    # look at tests that are not completely scanned
    for tref in Test.select().where(
        Test.scanned == False, Test.used == True, Test.identified == True  # noqa: E712
    ):
        # list starts with the sid.
        question_list = [tref.idgroups[0].student_id]
        for qref in tref.qgroups.order_by(QGroup.question):
            # if no HW pages scanned then display a hwpage 1 as unscanned.
            # note - there will always be tpages - so must check that they are scanned.
            # make sure no tpages for that group are scanned.
            if qref.group.hwpages.count() == 0:
                if any([pref.scanned for pref in qref.group.tpages]):
                    pass  # there is a scanned tpage present in that question - so skip
                else:
                    question_list.append(qref.question)
        if len(question_list) > 1:
            incomp_dict[tref.test_number] = question_list
    log.debug("Sending list of missing hw questions")
    return incomp_dict


def RgetUnusedTests(self):
    """Return list of tests (by testnumber) that have not been used - ie no test-pages scanned, no hw pages scanned."""
    unused_list = []
    for tref in Test.select().where(Test.used == False):  # noqa: E712
        unused_list.append(tref.test_number)
    log.debug("Sending list of unused tests")
    return unused_list


def RgetIdentified(self):
    """
    Return dict of identified tests - ie ones for which student ID/name are known.
    Indexed by test-number, lists pairs (student_id/student_name).
    Note that this includes papers which are not completely scanned.
    """
    idd_dict = {}
    for iref in IDGroup.select().where(IDGroup.identified == True):  # noqa: E712
        idd_dict[iref.test.test_number] = (iref.student_id, iref.student_name)
    log.debug("Sending list of identified tests")
    return idd_dict


def RgetNotAutoIdentified(self):
    """
    Return list of test numbers of scanned but unidentified tests.
    See also IDgetImagesOfUnIDd
    """
    unidd_list = []
    hal_ref = User.get(User.name == "HAL")
    query = Group.select().where(
        Group.group_type == "i", Group.scanned == True  # noqa: E712
    )
    for gref in query:
        # there is always exactly one idgroup here.
        # ignore those belonging to HAL - they are pre-id'd
        if gref.idgroups[0].user == hal_ref:
            continue
        unidd_list.append(gref.test.test_number)
    log.debug("Sending list of scanned but not auto-id'd tests")
    return unidd_list


def RgetProgress(self, spec, q, v):
    """For the given question/version return a simple progress summary = a dict with keys
    [numberScanned, numberMarked, numberRecent, avgMark, avgTimetaken,
    medianMark, minMark, modeMark, maxMark] and their values
    numberRecent = number done in the last hour.
    """
    # set up a time-delta of 1 hour for calc of number done recently.
    one_hour = timedelta(hours=1)

    NScanned = 0  # number scanned
    NMarked = 0  # number marked
    NRecent = 0  # number marked in the last hour
    SMTime = 0  # sum marking time - for computing average
    FullMark = int(
        spec["question"][str(q)]["mark"]
    )  # full mark for the given question/version

    mark_list = []

    for qref in (
        QGroup.select()
        .join(Group)
        .where(
            QGroup.question == q,
            QGroup.version == v,
            Group.scanned == True,  # noqa: E712
        )
    ):
        NScanned += 1
        if qref.marked is True:
            NMarked += 1
            mark_list.append(qref.annotations[-1].mark)
            SMTime += qref.annotations[-1].marking_time
            if datetime.now() - qref.annotations[-1].time < one_hour:
                NRecent += 1

    log.debug("Sending progress summary for Q{}v{}".format(q, v))

    # this function returns Nones if mark_list is empty
    if len(mark_list) == 0:
        return {
            "NScanned": NScanned,
            "NMarked": NMarked,
            "NRecent": NRecent,
            "fullMark": FullMark,
            "avgMTime": None,
            "avgMark": None,
            "minMark": None,
            "medianMark": None,
            "modeMark": None,
            "maxMark": None,
        }
    else:
        from statistics import mean, median, mode

        return {
            "NScanned": NScanned,
            "NMarked": NMarked,
            "NRecent": NRecent,
            "fullMark": FullMark,
            "avgMTime": SMTime / NMarked,
            "avgMark": mean(mark_list),
            "minMark": min(mark_list),
            "medianMark": median(mark_list),
            "modeMark": mode(mark_list),
            "maxMark": max(mark_list),
        }


def RgetMarkHistogram(self, q, v):
    """Return a dict of dicts containing histogram of marks for the given q/v as hist[user][question][mark]=count."""
    histogram = {}
    for qref in (
        QGroup.select()
        .join(Group)
        .where(
            QGroup.question == q,
            QGroup.version == v,
            QGroup.marked == True,  # noqa: E712
            Group.scanned == True,  # noqa: E712
        )
    ):
        # make sure user.name in histogram
        if qref.user.name not in histogram:
            histogram[qref.user.name] = {}
        # make sure the mark is in the dict for that user
        if qref.annotations[-1].mark not in histogram[qref.user.name]:
            histogram[qref.user.name][qref.annotations[-1].mark] = 0
        # add to the count.
        histogram[qref.user.name][qref.annotations[-1].mark] += 1
    log.debug("Sending mark histogram for Q{}v{}".format(q, v))
    return histogram


def RgetQuestionUserProgress(self, q, v):
    """For the given q/v return the number of questions marked by each user (who marked something in this q/v - so no zeros).
    Return a dict of the form [ number_scanned, [user, nmarked, avgtime], [user, nmarked,avgtime], etc]
    """
    user_counts = defaultdict(int)
    user_times = defaultdict(int)
    number_scanned = 0
    for qref in (
        QGroup.select()
        .join(Group)
        .where(
            QGroup.question == q,
            QGroup.version == v,
            Group.scanned == True,  # noqa: E712
        )
    ):
        number_scanned += 1
        if qref.marked is True:
            user_counts[qref.user.name] += 1
            user_times[qref.user.name] += qref.annotations[-1].marking_time
    # build return list
    progress = [number_scanned]
    for user in user_counts:
        progress.append(
            [user, user_counts[user], round(user_times[user] / user_counts[user])]
        )
    log.debug("Sending question/user progress for Q{}v{}".format(q, v))
    return progress


def RgetCompletionStatus(self):
    """Return a dict of every (ie whether completely scanned or not). Each dict entry is of the form dict[test_number] = [scanned_or_not, identified_or_not, number_of_questions_marked]"""
    progress = {}
    for tref in Test.select():
        number_marked = (
            QGroup.select()
            .where(QGroup.test == tref, QGroup.marked == True)  # noqa: E712
            .count()
        )
        progress[tref.test_number] = [tref.scanned, tref.identified, number_marked]
    log.debug("Sending list of completed tests")
    return progress


def RgetOutToDo(self):
    """Return a list of tasks that are currently out with clients. These have status "todo".
    For each task we return a triple of [code, user, time]
    code = id-t{testnumber} or mrk-t{testnumber}-q{question}-v{version}
    note that the datetime object is not jsonable, so we format it using strftime.
    """
    # note - have to format the time as string since not jsonable.
    # x.time.strftime("%y:%m:%d-%H:%M:%S"),

    out_tasks = []
    for iref in IDGroup.select().where(IDGroup.status == "out"):
        out_tasks.append(
            [
                "id-t{}".format(iref.test.test_number),
                iref.user.name,
                iref.time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    for qref in QGroup.select().where(QGroup.status == "out"):
        out_tasks.append(
            [
                "mrk-t{}-q{}-v{}".format(
                    qref.test.test_number, qref.question, qref.version
                ),
                qref.user.name,
                qref.time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    log.debug("Sending list of tasks that are still out")
    return out_tasks


def RgetStatus(self, test_number):
    """For the given test_number return detailed status information.
    Return a dict containing keys and values
    * number = test_number
    * identified = id'd or not (boolean)
    * marked = marked or not (boolean)
    Then if id'd we also add keys/values
    * sid = student id
    * sname = student name
    * iwho = who did the id-ing.
    For each question then add a sub-dict with key = that question number, and key/values
    * marked = marked or not
    * version = the version of that question
    if marked also add
    * mark = the score
    * who = who did the marking.
    """
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    state = {
        "number": tref.test_number,
        "identified": tref.identified,
        "marked": tref.marked,
    }
    if tref.identified:
        iref = tref.idgroups[0]
        state["sid"] = iref.student_id
        state["sname"] = iref.student_name
        state["iwho"] = iref.user.name
    for qref in tref.qgroups:
        if qref.marked:
            state[qref.question] = {
                "marked": True,
                "version": qref.version,
                "mark": qref.annotations[-1].mark,
                "who": qref.annotations[-1].user.name,
            }
        else:
            state[qref.question] = {
                "marked": False,
                "version": qref.version,
            }

    log.debug("Sending status of test {}".format(test_number))
    return [True, state]


def RgetSpreadsheet(self):
    """Return a dict that contains all the information needed to build the spreadsheet."""
    # build a spreadsheet dict indexed by test_number
    # each value that dict is a dict which contains the info about that test
    sheet = {}
    # look for all tests that are completely scanned.
    for tref in Test.select().where(Test.scanned == True):  # noqa: E712
        # a dict for the current test.
        this_test = {
            "identified": tref.identified,  # id'd or not
            "marked": tref.marked,  # completely marked or not
            "sid": "",  # blank entry for student id - replaced if id'd
            "sname": "",  # blank entry for student name - replaced if id'd
        }
        # if identified update sid, sname.
        iref = tref.idgroups[0]
        if tref.identified:  # set the sid and sname.
            this_test["sid"] = iref.student_id
            this_test["sname"] = iref.student_name
        # check each question (in order)
        for qref in tref.qgroups.order_by(QGroup.question):
            # store the version and mark
            this_test["q{}v".format(qref.question)] = qref.version
            this_test["q{}m".format(qref.question)] = ""  # blank unless marked
            if qref.marked:  # if marked, updated.
                this_test["q{}m".format(qref.question)] = qref.annotations[-1].mark
        # insert the data for this_test into the spreadsheet dict.
        sheet[tref.test_number] = this_test
    log.debug("Sending spreadsheet data.")
    return sheet


def RgetOriginalFiles(self, test_number):
    """Return list of the filenames for the original (unannotated) page images for the given test.

    Lightly deprecated: but still used by reassembly of only-IDed (offline graded) papers.
    """
    page_files = []
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return []
    # append tpages, hwpages and then expages.
    for pref in tref.tpages.order_by(TPage.page_number):
        if pref.scanned:
            page_files.append(pref.image.file_name)
    for qref in tref.qgroups.order_by(QGroup.question):
        for pref in qref.group.hwpages:
            page_files.append(pref.image.file_name)
        for pref in qref.group.expages:
            page_files.append(pref.image.file_name)

    log.debug("Sending original images of test {}".format(test_number))
    return page_files


def RgetCoverPageInfo(self, test_number):
    """For the given test, return information to build the coverpage for the test.
    We return a list of the form
    [[student_id, student_name], [question, version, mark]-for each question]
    """
    # todo - put in sanity / safety checks

    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return []
    # [ID, Name]
    iref = tref.idgroups[0]
    coverpage = [[iref.student_id, iref.student_name]]
    # then [q, v, mark]
    for qref in tref.qgroups.order_by(QGroup.question):
        coverpage.append([qref.question, qref.version, qref.annotations[-1].mark])
    log.debug("Sending coverpage info of test {}".format(test_number))
    return coverpage


def RgetMarkReview(self, filterQ, filterV, filterU, filterM):
    """Return a list of all marked qgroups satisfying the filter conditions.
    Filter on question-number, version, and user-name.
    For each matching qgroup we return a tuple of
    [testnumber, question, version, mark of latest annotation, username, marking_time, time finished.]
    """
    if filterM is True:
        query = QGroup.select().join(User).where(QGroup.marked == True)  # noqa: E712
    else:
        query = QGroup.select()
    if filterQ != "*":
        query = query.where(QGroup.question == filterQ)
    if filterV != "*":
        query = query.where(QGroup.version == filterV)
    if filterU != "*":
        query = query.where(User.name == filterU)
    filtered = []
    for qref in query:
        if qref.marked is True:
            filtered.append(
                [
                    qref.test.test_number,
                    qref.question,
                    qref.version,
                    qref.annotations[-1].mark,
                    qref.user.name,
                    qref.annotations[-1].marking_time,
                    # CANNOT JSON DATETIMEFIELD.
                    qref.annotations[-1].time.strftime("%y:%m:%d-%H:%M:%S"),
                ]
            )
        else:
            filtered.append(
                [
                    qref.test.test_number,
                    qref.question,
                    qref.version,
                    "n/a",  # mark
                    "unmarked",  # username
                    "n/a",  # marking time
                    "n/a",  # when
                ]
            )

    log.debug(
        "Sending filtered mark-review data. filters (Q,V,U)={}.{}.{}".format(
            filterQ, filterV, filterU
        )
    )
    log.warn(f"FILT = {filtered}")
    return filtered


def RgetIDReview(self):
    """Return information about every identified paper.
    For each paper return a tuple of [test_number, who did the iding, the time, the student ID, and the student name]
    """
    id_paper_list = []
    query = IDGroup.select().where(IDGroup.identified == True)  # noqa: E712
    for iref in query:
        id_paper_list.append(
            [
                iref.test.test_number,
                iref.user.name,
                iref.time.strftime("%y:%m:%d-%H:%M:%S"),
                iref.student_id,
                iref.student_name,
            ]
        )
    log.debug("Sending ID review data")
    return id_paper_list


def RgetUserFullProgress(self, user_name):
    """Return the number of completed tasks of teach type for the given user.
    Return [ number_id'd, number_marked]
    number_marked = number marked for all questions.
    """
    uref = User.get_or_none(name=user_name)
    if uref is None:
        return []
    # return [#IDd, #marked]
    log.debug("Sending user {} progress data".format(user_name))
    return [
        IDGroup.select()
        .where(IDGroup.user == uref, IDGroup.identified == True)  # noqa: E712
        .count(),
        QGroup.select()
        .where(QGroup.user == uref, QGroup.marked == True)  # noqa: E712
        .count(),
    ]


###
