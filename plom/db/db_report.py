from plom.db.tables import *
from datetime import datetime, timedelta

import logging

log = logging.getLogger("DB")

# ------------------
# Reporting functions


def RgetScannedTests(self):
    rval = {}
    for tref in Test.select().where(Test.scanned == True):
        pScanned = []
        # first append test-pages
        for p in tref.tpages:
            if p.scanned == True:
                pScanned.append(["t.{}".format(p.page_number), p.version])
        # then append hw-pages in question-order
        for qref in tref.qgroups:
            gref = qref.group
            for p in gref.hwpages:
                pScanned.append(["hw.{}.{}".format(qref.question, p.order), p.version])
        # then append x-pages in order
        for p in tref.lpages:
            pScanned.append(["x.{}".format(p.order), 0])  # we don't know the version
        rval[tref.test_number] = pScanned
    log.debug("Sending list of scanned tests")
    return rval


def RgetIncompleteTests(self):
    rval = {}
    for tref in Test.select().where(Test.scanned == False, Test.used == True):
        pState = []
        for p in tref.tpages:
            pState.append(["t.{}".format(p.page_number), p.version, p.scanned])
        # then append hw-pages in question-order
        for qref in tref.qgroups:
            gref = qref.group
            for p in gref.hwpages:
                pScanned.append(
                    ["hw.{}.{}".format(qref.question, p.order), p.version, True]
                )
        # then append x-pages in order
        for p in tref.lpages:
            pScanned.append(
                ["x.{}".format(p.order), 0, True]
            )  # we don't know the version
        rval[tref.test_number] = pState
    log.debug("Sending list of incomplete tests")
    return rval


def RgetUnusedTests(self):
    rval = []
    for tref in Test.select().where(Test.used == False):
        rval.append(tref.test_number)
    log.debug("Sending list of unused tests")
    return rval


def RgetIdentified(self):
    rval = {}
    for iref in IDGroup.select().where(IDGroup.identified == True):
        rval[iref.test.test_number] = (iref.student_id, iref.student_name)
    log.debug("Sending list of identified tests")
    return rval


def RgetProgress(self, q, v):
    # return [numberScanned, numberMarked, numberRecent, avgMark, avgTimetaken]
    oneHour = timedelta(hours=1)
    NScanned = 0
    NMarked = 0
    NRecent = 0
    SMark = 0
    SMTime = 0
    for x in (
        QGroup.select()
        .join(Group)
        .where(QGroup.question == q, QGroup.version == v, Group.scanned == True,)
    ):
        NScanned += 1
        if x.marked == True:
            NMarked += 1
            SMark += x.annotations[-1].mark
            SMTime += x.annotations[-1].marking_time
            if datetime.now() - x.annotations[-1].time < oneHour:
                NRecent += 1

    log.debug("Sending progress summary for Q{}v{}".format(q, v))
    if NMarked == 0:
        return {
            "NScanned": NScanned,
            "NMarked": NMarked,
            "NRecent": NRecent,
            "avgMark": None,
            "avgMTime": None,
        }
    else:
        return {
            "NScanned": NScanned,
            "NMarked": NMarked,
            "NRecent": NRecent,
            "avgMark": SMark / NMarked,
            "avgMTime": SMTime / NMarked,
        }


def RgetMarkHistogram(self, q, v):
    rhist = {}
    # defaultdict(lambda: defaultdict(int))
    for x in (
        QGroup.select()
        .join(Group)
        .where(
            QGroup.question == q,
            QGroup.version == v,
            QGroup.marked == True,
            Group.scanned == True,
        )
    ):
        # make sure user.name and mark both in histogram
        if x.user.name not in rhist:
            rhist[x.user.name] = {}
        if x.annotations[-1].mark not in rhist[x.user.name]:
            rhist[x.user.name][x.annotations[-1].mark] = 0
        rhist[x.user.name][x.annotations[-1].mark] += 1
    log.debug("Sending mark histogram for Q{}v{}".format(q, v))
    return rhist


def RgetMarked(self, q, v):
    rval = []
    for x in (
        QuestionData.select()
        .join(Group)
        .where(
            QuestionData.questionNumber == q,
            QuestionData.version == v,
            QuestionData.marked == True,
            Group.scanned == True,
        )
    ):
        rval.append(x.group.gid)
    log.debug("Sending list of marked tasks for Q{}V{}".format(q, v))
    return rval


def RgetQuestionUserProgress(self, q, v):
    # return [ nScanned, [user, nmarked], [user, nmarked], etc]
    rdat = {}
    nScan = 0
    for x in (
        QGroup.select()
        .join(Group)
        .where(QGroup.question == q, QGroup.version == v, Group.scanned == True,)
    ):
        nScan += 1
        if x.marked == True:
            if x.user.name not in rdat:
                rdat[x.user.name] = 0
            rdat[x.user.name] += 1
    rval = [nScan]
    for x in rdat:
        rval.append([x, rdat[x]])
    log.debug("Sending question/user progress for Q{}v{}".format(q, v))
    return rval


def RgetCompletions(self):
    rval = {}
    for tref in Test.select().where(Test.scanned == True):
        numMarked = (
            QGroup.select().where(QGroup.test == tref, QGroup.marked == True).count()
        )
        rval[tref.test_number] = [tref.identified, tref.totalled, numMarked]
    log.debug("Sending list of completed tests")
    return rval


def RgetOutToDo(self):
    # return list of tasks that are status = todo
    # note - have to format the time as string since not jsonable.
    # x.time.strftime("%y:%m:%d-%H:%M:%S"),

    rval = []
    for iref in IDGroup.select().where(IDGroup.status == "out"):
        rval.append(
            [
                "id-t{}".format(iref.test.test_number),
                iref.user.name,
                iref.time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    for qref in QGroup.select().where(QGroup.status == "out"):
        rval.append(
            [
                "mrk-t{}-q{}-v{}".format(
                    qref.test.test_number, qref.question, qref.version
                ),
                qref.user.name,
                qref.annotations[-1].time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    for sref in SumData.select().where(SumData.status == "out"):
        rval.append(
            [
                "tot-t{}".format(sref.test.test_number),
                sref.user.name,
                sref.time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    log.debug("Sending list of tasks that are still out")
    return rval


def RgetStatus(self, test_number):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    rval = {
        "number": tref.test_number,
        "identified": tref.identified,
        "marked": tref.marked,
        "totalled": tref.totalled,
    }
    if tref.identified:
        iref = tref.idgroups[0]
        rval["sid"] = iref.student_id
        rval["sname"] = iref.student_name
        rval["iwho"] = iref.user.name
    if tref.totalled:
        sref = tref.sumdata[0]
        rval["total"] = sref.sum_mark
        rval["twho"] = sref.user.name
    for qref in tref.qgroups:
        if qref.marked:
            rval[qref.question] = {
                "marked": True,
                "version": qref.version,
                "mark": qref.annotations[-1].mark,
                "who": qref.annotations[-1].user.name,
            }
        else:
            rval[qref.question] = {
                "marked": False,
                "version": qref.version,
            }

    log.debug("Sending status of test {}".format(test_number))
    return [True, rval]


def RgetSpreadsheet(self):
    rval = {}
    for tref in Test.select().where(Test.scanned == True):
        thisTest = {
            "identified": tref.identified,
            "marked": tref.marked,
            "totalled": tref.totalled,
            "sid": "",
            "sname": "",
        }
        iref = tref.idgroups[0]
        if tref.identified:
            thisTest["sid"] = iref.student_id
            thisTest["sname"] = iref.student_name
        for qref in tref.qgroups:
            thisTest["q{}v".format(qref.question)] = qref.version
            thisTest["q{}m".format(qref.question)] = ""
            if qref.marked:
                thisTest["q{}m".format(qref.question)] = qref.annotations[-1].mark
        rval[tref.test_number] = thisTest
    log.debug("Sending spreadsheet (effectively)")
    return rval


def RgetOriginalFiles(self, test_number):
    rval = []
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return []
    for p in tref.pages.order_by(Page.page_number):
        rval.append(p.file_name)
    log.debug("Sending original images of test {}".format(test_number))
    return rval


def RgetCoverPageInfo(self, test_number):
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return []
    # [ID, Name]
    iref = tref.idgroups[0]
    rval = [[iref.student_id, iref.student_name]]
    # then [q, v, mark]
    for g in tref.qgroups.order_by(QGroup.question):
        rval.append([g.question, g.version, g.annotations[-1].mark])
    log.debug("Sending coverpage info of test {}".format(test_number))
    return rval


def RgetAnnotatedFiles(self, test_number):
    rval = []
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return []
    # append ID-pages, then DNM-pages, then QuestionGroups
    idref = IDGroup.get_or_none(test=tref)
    for p in idref.idpages.order_by(IDPage.order):
        rval.append(p.image.file_name)
    # append DNM pages
    dnmref = DNMGroup.get_or_none(test=tref)
    for p in dnmref.dnmpages.order_by(DNMPage.order):
        rval.append(p.image.file_name)
    # append questiongroups
    for g in tref.qgroups.order_by(QGroup.question):
        rval.append(g.annotations[-1].image.file_name)
    log.debug("Sending annotated images for test {}".format(test_number))
    return rval


def RgetMarkReview(self, filterQ, filterV, filterU):
    query = QGroup.select().join(User).where(QGroup.marked == True)
    if filterQ != "*":
        query = query.where(QGroup.question == filterQ)
    if filterV != "*":
        query = query.where(QGroup.version == filterV)
    if filterU != "*":
        query = query.where(User.name == filterU)
    rval = []
    for x in query:
        rval.append(
            [
                x.test.test_number,
                x.question,
                x.version,
                x.annotations[-1].mark,
                x.user.name,
                x.annotations[-1].marking_time,
                # CANNOT JSON DATETIMEFIELD.
                x.annotations[-1].time.strftime("%y:%m:%d-%H:%M:%S"),
            ]
        )
    log.debug(
        "Sending filtered mark-review data. filters (Q,V,U)={}.{}.{}".format(
            filterQ, filterV, filterU
        )
    )
    return rval


def RgetAnnotatedImage(self, test_number, question, version):
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False]
    qref = QGroup.get_or_none(
        QGroup.test == tref,
        QGroup.question == question,
        QGroup.version == version,
        QGroup.marked == True,
    )
    if qref is None:
        return [False]
    log.debug(
        "Sending annotated image of tqv {}.{}.{}".format(test_number, question, version)
    )
    return [True, qref.annotations[-1].image.file_name]


def RgetIDReview(self):
    rval = []
    query = IDGroup.select().where(IDGroup.identified == True)
    for x in query:
        rval.append(
            [
                x.test.test_number,
                x.user.name,
                x.time.strftime("%y:%m:%d-%H:%M:%S"),
                x.student_id,
                x.student_name,
            ]
        )
    log.debug("Sending ID review data")
    return rval


def RgetTotReview(self):
    rval = []
    query = SumData.select().where(SumData.summed == True)
    for x in query:
        rval.append(
            [
                x.test.test_number,
                x.user.name,
                x.time.strftime("%y:%m:%d-%H:%M:%S"),
                x.sum_mark,
            ]
        )
    log.debug("Sending totalling review data")
    return rval


def RgetUserFullProgress(self, uname):
    uref = User.get_or_none(name=uname)
    if uref is None:
        return []
    # return [#IDd, #tot, #marked]
    log.debug("Sending user {} progress data".format(uname))
    return [
        IDGroup.select()
        .where(IDGroup.user == uref, IDGroup.identified == True)
        .count(),
        SumData.select().where(SumData.user == uref, SumData.summed == True).count(),
        QGroup.select().where(QGroup.user == uref, QGroup.marked == True).count(),
    ]
