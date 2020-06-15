from plom.db.tables import *
from datetime import datetime

import logging

log = logging.getLogger("DB")

# ------------------
# Marker stuff


def McountAll(self, q, v):
    """Count all the records"""
    try:
        return (
            QGroup.select()
            .join(Group)
            .where(QGroup.question == q, QGroup.version == v, Group.scanned == True,)
            .count()
        )
    except QGroup.DoesNotExist:
        return 0


def McountMarked(self, q, v):
    """Count all the Marked records"""
    try:
        return (
            QGroup.select()
            .join(Group)
            .where(
                QGroup.question == q,
                QGroup.version == v,
                QGroup.status == "done",
                Group.scanned == True,
            )
            .count()
        )
    except QGroup.DoesNotExist:
        return 0


def MgetDoneTasks(self, uname, q, v):
    """When a id-client logs on they request a list of papers they have already Marked.
    Send back the list."""
    uref = User.get(name=uname)  # authenticated, so not-None

    query = QGroup.select().where(
        QGroup.user == uref,
        QGroup.question == q,
        QGroup.version == v,
        QGroup.status == "done",
    )
    markList = []
    for x in query:
        aref = x.annotations[-1]
        markList.append(
            [x.group.gid, x.status, aref.mark, aref.marking_time, aref.tags]
        )
    log.debug('Sending completed Q{}v{} tasks to user "{}"'.format(q, v, uname))
    return markList


def MgetNextTask(self, q, v):
    """Find unid'd test and send test_number to client"""
    with plomdb.atomic():
        try:
            x = (
                QGroup.select()
                .join(Group)
                .where(
                    QGroup.status == "todo",
                    QGroup.question == q,
                    QGroup.version == v,
                    Group.scanned == True,
                )
                .get()
            )
        except QGroup.DoesNotExist as e:
            log.info("Nothing left on Q{}v{} to-do pile".format(q, v))
            return None

        log.debug("Next Q{}v{} task = {}".format(q, v, x.group.gid))
        return x.group.gid


def MgiveTaskToClient(self, uname, groupID):
    uref = User.get(name=uname)  # authenticated, so not-None
    try:
        with plomdb.atomic():
            gref = Group.get_or_none(Group.gid == groupID)
            if gref.scanned == False:
                return [False]
            qref = gref.qgroups[0]
            if qref.user is None or qref.user == uref:
                pass
            else:  # has been claimed by someone else.
                return [False]
            # update status, username
            qref.status = "out"
            qref.user = uref
            qref.save()
            # update the associate annotation
            # - create a new annotation copied from the previous one
            aref = qref.annotations[-1]  # are these in right order
            nref = Annotation.create(
                qgroup=qref,
                user=uref,
                edition=aref.edition + 1,
                tags=aref.tags,
                time=datetime.now(),
            )
            # create its pages
            for p in aref.apages.order_by(APage.order):
                APage.create(annotation=nref, order=p.order, image=p.image)
            # update user activity
            uref.last_action = "Took M task {}".format(groupID)
            uref.last_activity = datetime.now()
            uref.save()
            # return [true, tags, page1, page2, etc]
            rval = [
                True,
                nref.tags,
            ]
            for p in nref.apages.order_by(APage.order):
                rval.append(p.image.file_name)
            log.debug('Giving marking task {} to user "{}"'.format(groupID, uname))
            return rval
    except Group.DoesNotExist:
        log.info("That question {} not known".format(groupID))
        return False


def MdidNotFinish(self, uname, groupID):
    """When user logs off, any images they have still out should be put
    back on todo pile
    """
    uref = User.get(name=uname)  # authenticated, so not-None

    try:
        with plomdb.atomic():
            gref = Group.get_or_none(Group.gid == groupID)
            if gref.scanned == False:
                return
            qref = gref.qgroups[0]
            # sanity check that user has task
            if qref.user == uref and qref.status == "out":
                pass
            else:  # has been claimed by someone else.
                return

            # update status, etc
            qref.status = "todo"
            qref.user = None
            qref.marked = False
            # delete the annotation and associated APages
            aref = qref.annotations[-1]
            for p in aref.apages:
                p.delete_instance()
            aref.delete_instance()
            # now clean up the qgroup
            qref.test.marked = False
            qref.test.save()
            aref.save()
            qref.save()
            # Log user returning given tgv.
            log.info("User {} did not mark task {}".format(uname, groupID))

    except Group.DoesNotExist:
        log.info("That task {} not known".format(groupID))
        return False


def MtakeTaskFromClient(self, task, uname, mark, aname, pname, cname, mtime, tags, md5):
    """Get marked image back from client and update the record
    in the database.
    """
    uref = User.get(name=uname)  # authenticated, so not-None
    try:
        with plomdb.atomic():
            gref = Group.get_or_none(Group.gid == task)
            qref = gref.qgroups[0]

            if qref.user != uref:
                return False  # has been claimed by someone else.

            # update status, mark, annotate-file-name, time, and
            # time spent marking the image
            qref.status = "done"
            qref.marked = True
            aref = qref.annotations[-1]
            aref.image = Image.create(file_name=aname, md5sum=md5)
            aref.mark = mark
            aref.plom_file = pname
            aref.comment_file = cname
            aref.time = datetime.now()
            aref.marking_time = mtime
            aref.tags = tags
            qref.save()
            aref.save()
            # update user activity
            uref.last_action = "Returned M task {}".format(task)
            uref.last_activity = datetime.now()
            uref.save()
            # since this has been marked - check if all questions for test have been marked
            log.info(
                "Task {} marked {} by user {} and placed at {} with md5 = {}".format(
                    task, mark, uname, aname, md5
                )
            )
            tref = qref.test
            # check if there are any unmarked questions
            if (
                QGroup.get_or_none(QGroup.test == tref, QGroup.marked == False)
                is not None
            ):
                return True
            # update the sum-mark
            tot = 0
            for qd in QGroup.select().where(QGroup.test == tref):
                tot += qd.annotations[-1].mark
            sref = tref.sumdata[0]
            autref = User.get(name="HAL")
            sref.user = autref  # auto-totalled by HAL.
            sref.time = datetime.now()
            sref.sum_mark = tot
            sref.summed = True
            sref.status = "done"
            sref.save()
            log.info(
                "All of test {} is marked - total updated = {}".format(
                    tref.test_number, tot
                )
            )
            tref.marked = True
            tref.totalled = True
            tref.save()
            return True

    except Group.DoesNotExist:
        log.error(
            "That returning marking task number {} / user {} pair not known".format(
                task, uname
            )
        )
        return False


def MgetImages(self, uname, task):
    uref = User.get(name=uname)  # authenticated, so not-None
    try:
        with plomdb.atomic():
            gref = Group.get_or_none(Group.gid == task)
            if gref.scanned == False:
                return [False, "Task {} is not completely scanned".format(task)]
            qref = gref.qgroups[0]
            if qref.user != uref:
                # belongs to another user
                return [
                    False,
                    "Task {} does not belong to user {}".format(task, uname),
                ]
            # return [true, n, page1,..,page.n]
            # or
            # return [true, n, page1,..,page.n, annotatedFile, plom_file]
            pp = []
            aref = qref.annotations[-1]
            for p in aref.apages.order_by(APage.order):
                pp.append(p.image.file_name)
            if aref.image is not None:
                return [True, len(pp)] + pp + [aref.image.file_name, aref.plom_file]
            else:
                return [True, len(pp)] + pp
    except Group.DoesNotExist:
        log.info("Mgetimage - task {} not known".format(task))
        return False


def MgetOriginalImages(self, task):
    try:
        with plomdb.atomic():
            gref = Group.get(Group.gid == task)
            if gref.scanned == False:
                log.warning(
                    "MgetOriginalImages - task {} not completely scanned".format(task)
                )
                return [False, "Task {} is not completely scanned".format(task)]
            aref = gref.qgroups[0].annotations[0]  # the original annotation pages
            # return [true, page1,..,page.n]
            rval = [True]
            for p in aref.apages.order_by(APage.order):
                rval.append(p.image.file_name)
            return rval
    except Group.DoesNotExist:
        log.info("MgetOriginalImages - task {} not known".format(task))
        return [False, "Task {} not known".format(task)]


def MsetTag(self, uname, task, tag):
    uref = User.get(name=uname)  # authenticated, so not-None

    try:
        with plomdb.atomic():
            gref = Group.get(Group.gid == task)
            qref = gref.qgroups[0]
            if qref.user != uref:
                return False  # not your task
            # update tag
            qref.tags = tag
            qref.save()
            log.info('Task {} tagged by user "{}": "{}"'.format(task, uname, tag))
            return True
    except Group.DoesNotExist:
        log.error("MsetTag -  task {} / user {} pair not known".format(task, uname))
        return False


def MgetWholePaper(self, test_number, question):
    tref = Test.get_or_none(
        Test.test_number == test_number
    )  # show not totally scanned test.
    if tref is None:  # don't know that test - this shouldn't happen
        return [False]
    pageData = []
    pageFiles = []
    question = int(question)
    for p in tref.tpages.order_by(TPage.page_number):  # give TPages
        if p.scanned is False:  # skip unscanned testpages
            continue
        if p.group.group_type == "i":  # skip IDpages
            continue
        val = ["t{}".format(p.page_number), p.image.id, False]
        # check if page belongs to our question
        if p.group.group_type == "q":
            if p.group.qgroups[0].question == question:
                val[2] = True
        pageData.append(val)
        pageFiles.append(p.image.file_name)
    for p in tref.hwpages.order_by(HWPage.order):  # then give HWPages
        if p.group.group_type == "i":  # skip IDpages
            continue
        elif p.group.group_type == "d":  # is DNM group
            q = 0
        else:
            q = p.group.qgroups[0].question
        val = ["h{}.{}".format(q, p.order), p.image.id, False]
        # check if page belongs to our question
        if p.group.group_type == "q":
            if p.group.qgroups[0].question == question:
                val[2] = True
        pageData.append(val)
        pageFiles.append(p.image.file_name)
    for p in tref.lpages.order_by(LPage.order):  # then give HWPages
        val = ["x{}".format(p.order), p.image.id, False]
        pageData.append(val)
        pageFiles.append(p.image.file_name)
    return [True, pageData] + pageFiles


def MshuffleImages(self, uname, task, imageRefs):
    uref = User.get(name=uname)  # authenticated, so not-None

    with plomdb.atomic():
        gref = Group.get(Group.gid == task)
        qref = gref.qgroups[0]
        if qref.user != uref:
            return [False]  # not your task
        # grab the last annotation
        aref = gref.qgroups[0].annotations[-1]
        # delete the old pages
        for p in aref.apages:
            p.delete_instance()
        # now create new apages
        ord = 0
        for ir in imageRefs:
            ord += 1
            APage.create(annotation=aref, image=ir, order=ord)
        aref.time = datetime.now()
        uref.last_activity = datetime.now()
        uref.last_action = "Shuffled images of {}".format(task)
        aref.save()
        uref.save()
    log.info("MshuffleImages - task {} now irefs {}".format(task, imageRefs))
    return [True]


def MreviewQuestion(self, test_number, question, version):
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
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
    with plomdb.atomic():
        qref.user = revref
        qref.time = datetime.now()
        qref.save()
    log.info("Setting tq {}.{} for reviewer".format(test_number, question))
    return [True]


def MrevertTask(self, task):
    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        return [False, "NST"]  # no such task
    # from the group get the test, question and sumdata - all need cleaning.
    qref = gref.qgroups[0]
    tref = gref.test
    sref = tref.sumdata[0]
    # check task is "done"
    if qref.status != "done" or qref.marked is False:
        return [False, "NAC"]  # nothing to do here
    # now update things
    log.info("Manager reverting task {}".format(task))
    with plomdb.atomic():
        # clean up test
        tref.marked = False
        tref.totalled = False
        tref.save()
        # clean up sum-data - no one should be totalling and marking at same time.
        # TODO = sort out the possible idiocy caused by simultaneous marking+totalling by client.
        sref.status = "todo"
        sref.sum_mark = None
        sref.user = None
        sref.time = datetime.now()
        sref.summed = False
        sref.save()
        # clean off the question data - remove user and set status back to todo
        rval = [True, qref.annotatedFile, qref.plom_file, qref.comment_file]
        qref.marked = False
        qref.status = "todo"
        qref.user = None
        qref.annotatedFile = None
        qref.md5sum = None
        qref.plom_file = None
        qref.comment_file = None
        qref.mark = None
        qref.marking_time = None
        qref.tags = ""
        qref.time = datetime.now()
        qref.save()
        # update user activity
        uref.last_action = "Reverted M task {}".format(task)
        uref.last_activity = datetime.now()
        uref.save()
    log.info("Reverting tq {}.{}".format(test_number, question))
    return rval
