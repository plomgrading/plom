# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022, 2024 Colin B. Macdonald
# Copyright (C) 2021 Nicholas J H Lai

from collections import defaultdict
import logging
from time import time

from plom.db.tables import (
    Group,
    IDGroup,
    QGroup,
    Test,
    TPage,
    HWPage,
    EXPage,
    User,
    Annotation,
)
from plom.misc_utils import datetime_to_json, is_within_one_hour_of_now


log = logging.getLogger("DB")


# ------------------
# Reporting functions


def RgetScannedTests(self):
    """Get a dict of all scanned tests indexed by test_number.
    Each test lists pairs [page-code, page-version].
    page-code is t.{page}, h.{question}.{order}, or e.{question}.{order}.
    """

    t0 = time()  # to compute time this takes
    # some code for prefetching things to make this query much faster
    # roughly - build queries for each of these sets of objects that we need
    # tests, tpages, qgroups, groups, hwpages, pages
    the_tests = Test.select().where(Test.scanned == True)  # noqa: E712
    the_pages = TPage.select().where(TPage.scanned == True)  # noqa: E712
    the_qgroups = QGroup.select()
    the_groups = Group.select().where(Group.group_type == "q")
    the_hwpages = HWPage.select()
    the_expages = EXPage.select()

    # first populate the dict with empty lists for each scanned test
    redux = {tref.test_number: [] for tref in the_tests}
    # use prefetch to get peewee to pre-load the tpages
    for tref in the_tests.prefetch(the_pages):
        redux[tref.test_number] += [
            ["t.{}".format(p.page_number), p.version] for p in tref.tpages
        ]
    # use prefetch to preload the qgroups, groups and hwpages
    for tref in the_tests.prefetch(the_qgroups, the_groups, the_hwpages):
        for qref in tref.qgroups:
            gref = qref.group
            q = qref.question
            redux[tref.test_number] += [
                [f"h.{q}.{p.order}", p.version] for p in gref.hwpages
            ]

    # use prefetch to preload the qgroups, groups and expages
    for tref in the_tests.prefetch(the_qgroups, the_groups, the_expages):
        for qref in tref.qgroups:
            gref = qref.group
            q = qref.question
            redux[tref.test_number] += [
                [f"e.{q}.{p.order}", p.version] for p in gref.expages
            ]

    log.debug(f"Sending list of scanned tests - took {time() - t0}s")
    return redux


def RgetIncompleteTests(self):
    """Get dict of incomplete tests - ie some test pages scanned but not all.

    Indexed by test_number
    Each test lists triples [page-code, version, scanned_or_not].
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
                        "original_name": pref.image.original_name,
                        "bundle_name": pref.image.bundle.name,
                        "bundle_order": pref.image.bundle_order,
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
                    "original_name": pref.image.original_name,
                    "bundle_name": pref.image.bundle.name,
                    "bundle_order": pref.image.bundle_order,
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
                    "original_name": pref.image.original_name,
                    "bundle_name": pref.image.bundle.name,
                    "bundle_order": pref.image.bundle_order,
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
    # TODO - fix this for new prediction table stuff
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

    NScanned = 0  # number scanned
    NMarked = 0  # number marked
    NRecent = 0  # number marked in the last hour
    SMTime = 0  # sum marking time - for computing average
    FullMark = int(
        spec["question"][str(q)]["mark"]
    )  # full mark for the given question/version

    mark_list = []

    t0 = time()
    # faster prefetch code - replacing slower legacy code.
    the_qgroups = (
        QGroup.select(QGroup, Group)
        .join(Group)
        .where(
            QGroup.question == q,
            QGroup.version == v,
            Group.scanned == True,  # noqa: E712
        )
    )
    the_annotations = Annotation.select()
    for qref in the_qgroups.prefetch(the_annotations):
        # TODO work out how to get the last annotation for each qgroup. Seems a little hard.
        aref = qref.annotations[-1]
        NScanned += 1
        if qref.marked is True:
            NMarked += 1
            mark_list.append(aref.mark)
            SMTime += aref.marking_time
            if is_within_one_hour_of_now(aref.time):
                NRecent += 1

    log.debug(f"Sending progress summary for Q{q}v{v} = took {time() - t0}s")

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
    """Return a dict of every (ie whether completely scanned or not).
    Each dict entry is of the form
    dict[test_number] = [scanned_or_not, identified_or_not, number_of_questions_marked, time_of_last_update]
    """
    t0 = time()
    progress = {}
    # to hold the ID-group last update for each test between loops over tests
    last_update_dict = {}
    the_tests = Test.select()
    the_idg = IDGroup.select()
    the_qg = QGroup.select()

    # get the last update time for each idgroup
    for tref in the_tests.prefetch(the_idg):
        last_update_dict[tref.test_number] = tref.idgroups[0].time
    # now loop over each question
    for tref in the_tests.prefetch(the_qg):
        number_marked = 0
        last_update = last_update_dict[tref.test_number]
        for qref in tref.qgroups:
            if qref.marked:
                number_marked += 1
            if last_update < qref.time:
                last_update = qref.time
        progress[tref.test_number] = [
            tref.scanned,
            tref.identified,
            number_marked,
            datetime_to_json(last_update),
        ]
    log.debug(f"Sending list of completed tests = took {time() - t0}s")
    return progress


def RgetOutToDo(self):
    """Return a list of tasks that are currently out with clients. These have status "todo".
    For each task we return a triple of [code, user, time]
    code = id-t{testnumber} or mrk-t{testnumber}-q{question}-v{version}
    note that the datetime object is not directly jsonable, so convert it to a
    string via datetime_to_json which uses arrow.
    """

    out_tasks = []
    for iref in IDGroup.select().where(IDGroup.status == "out"):
        out_tasks.append(
            [
                "id-t{}".format(iref.test.test_number),
                iref.user.name,
                datetime_to_json(iref.time),
            ]
        )
    for qref in QGroup.select().where(QGroup.status == "out"):
        out_tasks.append(
            [
                "mrk-t{}-q{}-v{}".format(
                    qref.test.test_number, qref.question, qref.version
                ),
                qref.user.name,
                datetime_to_json(qref.time),
            ]
        )
    log.debug("Sending list of tasks that are still out")
    return out_tasks


def RgetStatus(self, test_number):
    """For the given test_number return detailed status information.

    Return:
        dict: keys and values:

        * number = test_number
        * identified = id'd or not (boolean)
        * marked = marked or not (boolean)

        Then if id'd we also add keys/values:

        * sid = student id
        * sname = student name
        * iwho = who did the id-ing

        For each question then add a sub-dict with key = that question number, and key/values:

        * marked = marked or not
        * version = the version of that question

        if marked also add:

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
        # compute the time of last update across the idgroup and each qgroup
        last_update = tref.idgroups[0].time  # even if un-id'd will show creation time.
        # check each question (in order)
        for qref in tref.qgroups.order_by(QGroup.question):
            # store the version and mark
            this_test["q{}v".format(qref.question)] = qref.version
            this_test["q{}m".format(qref.question)] = ""  # blank unless marked
            if qref.marked:  # if marked, updated.
                this_test["q{}m".format(qref.question)] = qref.annotations[-1].mark
            if last_update < qref.time:
                last_update = qref.time
        # last_update time is now most recent group update time.
        this_test["last_update"] = datetime_to_json(last_update)
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


def RgetMarkReview(
    self,
    *,
    filterPaperNumber,
    filterQ,
    filterV,
    filterUser,
    filterMarked,
):
    """Return a list of all marked qgroups satisfying the filter conditions.

    Filter on paper-number, question-number, version, user-name and whether
    it is marked.  The string ``"*"`` is a wildcard to match all papers.
    TODO: how does type work here?  I guess they are either int/str,
    would it be better to use None/int with None as the wildcard?

    Returns:
        list-of-lists: for each matching qgroup we return a list of the form:
        `[testnumber, question, version, mark of latest annotation, username, marking_time, time finished]`.
    """
    t0 = time()
    query = QGroup.select()
    if filterMarked is True:
        query = query.where(QGroup.marked == True)  # noqa: E712
    if filterPaperNumber != "*":
        tref = Test.get_or_none(test_number=filterPaperNumber)
        if tref is None:
            return []
        query = query.where(QGroup.test == tref)
    if filterQ != "*":
        query = query.where(QGroup.question == filterQ)
    if filterV != "*":
        query = query.where(QGroup.version == filterV)
    if filterUser != "*":
        uref = User.get_or_none(name=filterUser)
        if uref is None:
            return []
        query = query.where(QGroup.user == uref)
    filtered = []
    for qref in query:
        tags = [t.tag.text for t in qref.questiontaglinks]
        if qref.marked is True:
            filtered.append(
                [
                    qref.test.test_number,
                    qref.question,
                    qref.version,
                    qref.annotations[-1].mark,
                    qref.user.name,
                    qref.annotations[-1].marking_time,
                    # Cannot json datetime, so convert it to string
                    datetime_to_json(qref.annotations[-1].time),
                    tags,
                ]
            )
        else:
            filtered.append(
                [
                    qref.test.test_number,
                    qref.question,
                    qref.version,
                    "n/a",  # mark
                    "<unmarked>",  # username
                    "n/a",  # marking time
                    "",  # when
                    tags,
                ]
            )

    log.debug("db.RgetMarkReview: %.3gs processing", time() - t0)
    log.debug("db.RgetMarkReview: sending %d rows of mark-review data", len(filtered))
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
                datetime_to_json(iref.time),
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


def _get_files_from_group(group_ref):
    """Return a list of images and their bundle info in the pages of the given group.

    args:
        group_ref: can be an IDGroup, DNMGroup or QGroup.

    returns:
        list: list of dicts with keys `original_name`, `bundle_name`,
        and `bundle_order`.

    Note: only scanned pages are included.
    """
    image_list = []
    # add all test_pages
    for pref in group_ref.tpages:
        if pref.scanned:  # only add if actually scanned
            image_list.append(
                {
                    "original_name": pref.image.original_name,
                    "bundle_name": pref.image.bundle.name,
                    "bundle_order": pref.image.bundle_order,
                }
            )
    # add all hw_pages and extra_pages
    for pref in group_ref.hwpages:
        image_list.append(
            {
                "original_name": pref.image.original_name,
                "bundle_name": pref.image.bundle.name,
                "bundle_order": pref.image.bundle_order,
            }
        )
    for pref in group_ref.expages:
        image_list.append(
            {
                "original_name": pref.image.original_name,
                "bundle_name": pref.image.bundle.name,
                "bundle_order": pref.image.bundle_order,
            }
        )
    return image_list


def RgetFilesInTest(self, test_number):
    """Return a list of images and their bundle info for all pages of the given test.

    args:
        test_number (int): which test.

    returns:
        dict: with keys ``"id"``, ``"dnm"``, ``"q1"``, ``"q2"``, etc.
        Each value is a list of dicts, one for each page.  Each of those
        dicts has keys `original_name`, `bundle_name`, `bundle_order`.
        Additional keys likely to be added.

    Note: only scanned pages are included.
    """
    file_dict = {}
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return file_dict

    for gref in tref.groups:
        image_list = _get_files_from_group(gref)
        if gref.group_type == "i":
            file_dict["id"] = image_list
        elif gref.group_type == "d":
            file_dict["dnm"] = image_list
        elif gref.group_type == "q":
            question = gref.qgroups[0].question
            file_dict[f"q{question}"] = image_list
    return file_dict


def RgetFilesInAllTests(self):
    """Return an audit of the files used in all the tests."""

    tests = {}
    for tref in Test.select():
        tests[tref.test_number] = self.RgetFilesInTest(tref.test_number)
    return tests
