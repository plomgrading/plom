# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from datetime import datetime
import json
import logging

import peewee as pw

from plom.db.tables import plomdb

from plom.db.tables import AImage, Annotation, APage, ARLink
from plom.db.tables import (
    Image,
    Group,
    QGroup,
    Rubric,
    Test,
    TPage,
    User,
    Tag,
    QuestionTagLink,
)

from plom.comment_utils import generate_new_comment_ID

log = logging.getLogger("DB")


# ------------------
# Marker stuff


def McountAll(self, q, v):
    """Count all the scanned q/v groups."""
    try:
        return (
            QGroup.select()
            .join(Group)
            .where(
                QGroup.question == q,
                QGroup.version == v,
                Group.scanned == True,  # noqa: E712
            )
            .count()
        )
    except pw.DoesNotExist:
        return 0


def McountMarked(self, q, v):
    """Count all the q/v groups that have been marked."""
    try:
        return (
            QGroup.select()
            .join(Group)
            .where(
                QGroup.question == q,
                QGroup.version == v,
                QGroup.status == "done",
                Group.scanned == True,  # noqa: E712
            )
            .count()
        )
    except pw.DoesNotExist:
        return 0


def MgetDoneTasks(self, user_name, q, v):
    """When a marker-client logs on they request a list of papers they have already marked.
    Send back the list of [group-ids, mark, marking_time, [list_of_tag_texts] ] for each paper.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None

    query = QGroup.select().where(
        QGroup.user == uref,
        QGroup.question == q,
        QGroup.version == v,
        QGroup.status == "done",
    )
    mark_list = []
    for qref in query:  # grab that questionData object
        # get the tag texts for that qgroup
        tag_list = [qtref.tag.text for qtref in qref.questiontaglinks]
        aref = qref.annotations[-1]  # grab the last annotation
        mark_list.append(
            [
                qref.group.gid,
                aref.mark,
                aref.marking_time,
                tag_list,
                aref.integrity_check,
            ]
        )
        # note - used to return qref.status, but is redundant since these all "done"
    log.debug('Sending completed Q{}v{} tasks to user "{}"'.format(q, v, user_name))
    return mark_list


def MgetNextTask(self, q, v):
    """Find unmarked (but scanned) q/v-group and send the group-id back to client."""
    with plomdb.atomic():
        try:
            qref = (
                QGroup.select()
                .join(Group)
                .where(
                    QGroup.status == "todo",
                    QGroup.question == q,
                    QGroup.version == v,
                    Group.scanned == True,  # noqa: E712
                )
                .get()
            )
            # as per #1811 - the user should be none here - assert here.
            assert (
                qref.user is None
            ), f"Marking-task for test {qref.test.test_number}, question {q} version {v} is todo, but has a user = {qref.user.name}"
        except pw.DoesNotExist:
            log.info("Nothing left on Q{}v{} to-do pile".format(q, v))
            return None

        log.debug("Next Q{}v{} task = {}".format(q, v, qref.group.gid))
        return qref.group.gid


def MgiveTaskToClient(self, user_name, group_id, version):
    """Assign a marking task to a certain user, and give them back needed data.

    args:
        user_name (str): the user name who is claiming the task.
        group_id (TODO): somehow tells the task (?).
        version (int): version requested - must match that in db.

    Return:
        list: On error, `[False, code, errmsg]` where `code` is a string:
            `"other_claimed"`, `"not_known"`, `"not_scanned"`, `"unexpected"`, `"mismatch"`
            and `errmsg` is a human-readable error message.
            Otherwise, the list is
                `[True, metadata, [list of tag texts], integrity_check]`
            where each row of `metadata` consists of
                `[DB_id, md5_sum, server_filename]`
            Note: `server_filename` is implementation-dependent, could change
            without notice, etc.  Clients could use this to get hints for a
            a local file name for example.

    question/version via group_id as a task to the given user, unless has been
    taken by another user.

    Create new annotation by copying the last one for that qdata - pages created when returned.
    """

    uref = User.get(name=user_name)  # authenticated, so not-None

    with plomdb.atomic():
        gref = Group.get_or_none(Group.gid == group_id)
        if gref is None:
            msg = f"The task {group_id} does not exist"
            log.info(msg)
            return [False, "no_such_task", msg]
        if not gref.scanned:
            msg = f"The task {group_id} is not scanned"
            log.info(msg)
            return [False, "not_scanned", msg]
        # grab the qdata corresponding to that group
        qref = gref.qgroups[0]
        if (qref.user is not None) and (qref.user != uref):
            # see also #1811 - if a task is "todo" then its user should be None.
            msg = f'Task {group_id} previously claimed by user "{qref.user.name}"'
            log.info(msg)
            return [False, "other_claimed", msg]
        # check the version matches that in the database
        if qref.version != version:
            msg = f"User asked for version {version} but task {group_id} has version {qref.version}."
            log.info(msg)
            return [False, "mismatch", msg]

        # Can only ask for tasks on the todo-pile... not ones in other states
        if qref.status != "todo":
            msg = f"Task {group_id} is not on the todo pile - we cannot give you another copy."
            log.info(msg)
            return [False, "not_todo", msg]

        # update status, username
        qref.status = "out"
        qref.user = uref
        qref.time = datetime.now()
        qref.save()
        # get tag_list
        tag_list = [qtref.tag.text for qtref in qref.questiontaglinks]
        # we give the marker the pages from the **existing** annotation
        # (when task comes back we create the new pages, new annotation etc)
        if len(qref.annotations) < 1:
            msg = f"unexpectedly, len(aref.annotations)={len(qref.annotations)}"
            msg += f", qref={qref}, group_id={group_id}"
            log.error(msg)
            return [False, "unexpected", msg]
        aref = qref.annotations[-1]  # are these in right order (TODO?)
        image_metadata = []
        for p in aref.apages.order_by(APage.order):
            image_metadata.append([p.image.id, p.image.md5sum, p.image.file_name])
        # update user activity
        uref.last_action = "Took M task {}".format(group_id)
        uref.last_activity = datetime.now()
        uref.save()
        log.debug(
            'Giving marking task {} to user "{}" with integrity_check {}'.format(
                group_id, user_name, aref.integrity_check
            )
        )
        return [True, image_metadata, tag_list, aref.integrity_check]


def MgetOneImageFilename(self, image_id, md5):
    """Get the filename of one image.

    Args:
        image_id: internal db ref number to image
        md5: the md5sum of that image (as sanity check)

    Returns:
        list: [True, file_name] or [False, error_msg] where
            error_msg is `"no such image"` or `"wrong md5sum"`.
            file_name is a string.
    """
    with plomdb.atomic():
        iref = Image.get_or_none(id=image_id)
        if iref is None:
            log.warning("Asked for a non-existent image with id={}".format(image_id))
            return [False, "no such image"]
        if iref.md5sum != md5:
            log.warning(
                "Asked for image id={} but supplied wrong md5sum {} instead of {}".format(
                    image_id, md5, iref.md5sum
                )
            )
            return [False, "wrong md5sum"]
        return [True, iref.file_name]


def MtakeTaskFromClient(
    self,
    task,
    user_name,
    mark,
    annot_fname,
    plom_fname,
    rubrics,
    marking_time,
    md5,
    integrity_check,
    image_md5_list,
):
    """Get marked image back from client and update the record
    in the database.
    Update the annotation.
    Check to see if all questions for that test are marked and if so update the test's 'marked' flag.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None

    with plomdb.atomic():
        # make sure all returned image-ids are actually images
        # keep the refs for apage creation
        image_ref_list = []
        for img_md5 in image_md5_list:
            iref = Image.get_or_none(md5sum=img_md5)
            if iref:
                image_ref_list.append(iref)
            else:
                return [False, "No_such_image"]

        # grab the group corresponding to that task
        gref = Group.get_or_none(Group.gid == task)
        if gref is None or not gref.scanned:  # this should not happen
            log.warning(
                "That returning marking task number {} / user {} pair not known".format(
                    task, user_name
                )
            )
            return [False, "no_such_task"]
        # and grab the qdata of that group
        qref = gref.qgroups[0]
        if qref.user != uref:  # this should not happen
            return [False, "not_owner"]  # has been claimed by someone else.
        # check the integrity_check code against the db
        # TODO: suspicious: client should probably tell us what annotation its work was based-on...
        oldaref = qref.annotations[-1]
        if oldaref.integrity_check != integrity_check:
            return [False, "integrity_fail"]
        # check all the images actually come from this test - sanity check against client error
        tref = qref.test
        # make a list of all the image-md5sums of all pages assoc with tref
        test_image_md5s = []
        for pref in tref.tpages:
            # tpages are always present - whether or not anything uploaded
            if pref.scanned:  # so only check scanned ones
                test_image_md5s.append(pref.image.md5sum)
        # other page types only present if used
        for pref in tref.hwpages:
            test_image_md5s.append(pref.image.md5sum)
        for pref in tref.expages:
            test_image_md5s.append(pref.image.md5sum)
        # check image_id_list against this list
        for img_md5 in image_md5_list:
            if img_md5 not in test_image_md5s:
                return [False, "image_not_in_test"]
        # check rubrics keys are valid
        # TODO - should these check question of rubric agrees with question of task?
        for rid in rubrics:
            if Rubric.get_or_none(key=rid) is None:
                return [False, "invalid_rubric"]

        aref = Annotation.create(
            qgroup=qref,
            user=uref,
            edition=oldaref.edition + 1,
            outdated=False,
            time=datetime.now(),
            integrity_check=oldaref.integrity_check,
        )
        # create apages from the image_ref_list.
        ord = 0
        for iref in image_ref_list:
            ord += 1
            APage.create(annotation=aref, order=ord, image=iref)

        # update status, mark, annotate-file-name, time, and
        # time spent marking the image
        qref.status = "done"
        qref.time = datetime.now()
        qref.marked = True
        # the bundle for this image is given by the (fixed) bundle for the parent qgroup.
        aref.aimage = AImage.create(file_name=annot_fname, md5sum=md5)
        aref.mark = mark
        aref.plom_file = plom_fname
        aref.marking_time = marking_time
        qref.save()
        aref.save()
        # update user activity
        uref.last_action = "Returned M task {}".format(task)
        uref.last_activity = datetime.now()
        uref.save()
        # since this has been marked - check if all questions for test have been marked
        log.info(
            "Task {} marked {} by user {} and placed at {} with md5 = {}".format(
                task, mark, user_name, annot_fname, md5
            )
        )
        # for each rubric used - make a link to the assoc rubric
        log.info("Recording rubrics, {}, used marking task {}".format(rubrics, task))
        for rid in rubrics:
            rref = Rubric.get_or_none(key=rid)
            rref.count += 1
            rref.save()
            if rref is None:  # this should not happen
                continue
            # check to see if it is already in
            arlref = ARLink.get_or_none(annotation=aref, rubric=rref)
            if arlref is None:
                ARLink.create(annotation=aref, rubric=rref)

        # check if there are any unmarked questions left in the test
        if (
            QGroup.get_or_none(
                QGroup.test == tref, QGroup.marked == False  # noqa: E712
            )
            is not None
        ):
            log.info("Still unmarked questions in test {}".format(tref.test_number))
            return [True, "more"]

        tref.marked = True
        tref.save()
        return [True, "test_done"]


def Mget_annotations(self, number, question, edition=None, integrity=None):
    """Retrieve the latest annotations, or a particular set of annotations.

    args:
        number (int): paper number.
        question (int): question number.
        edition (None/int): None means get the latest annotation, otherwise
            this controls which annotation set.  Larger number is newer.
        integrity (None/str): an optional checksum system the details of
            which I have forgotten.

    Returns:
        list: `[True, plom_file_data, annotation_image]` on success or
            on error `[False, error_msg]`.  If the task is not yet
            annotated, the error will be `"no_such_task"`.
    """
    if edition is None:
        edition = -1
    edition = int(edition)
    task = f"q{number:04}g{question}"
    with plomdb.atomic():
        gref = Group.get_or_none(Group.gid == task)
        if gref is None:
            log.info("M_get_annotations - task {} not known".format(task))
            return [False, "no_such_task"]
        if not gref.scanned:  # Sanity check - this should not happen.
            return [False, "no_such_task"]
        qref = gref.qgroups[0]
        if edition == -1:
            aref = qref.annotations[-1]
        else:
            aref = Annotation.get_or_none(qgroup=qref, edition=edition)
        if integrity:
            if aref.integrity_check != integrity:
                return [False, "integrity_fail"]
        # metadata for double-checking consistency with plom file
        metadata = []
        for p in aref.apages.order_by(APage.order):
            metadata.append([p.image.id, p.image.md5sum, p.image.file_name])
        if aref.aimage is None:
            return [False, "no_such_task"]
        plom_file = aref.plom_file
        img_file = aref.aimage.file_name
    with open(plom_file, "r") as f:
        plom_data = json.load(f)
    plom_data["user"] = aref.user.name
    plom_data["annotation_edition"] = aref.edition
    plom_data["annotation_reference"] = aref.id
    # Report any duplication in DB and plomfile (and keep DB version!)
    if plom_data["currentMark"] != aref.mark:
        log.warning("Plom file has wrong score, replacing")
        plom_data["currentMark"] = aref.mark
    for i, (id_, md5, _) in enumerate(metadata):
        if id_ != plom_data["base_images"][i]["id"]:
            log.warning("Plom file has wrong base image id, replacing")
            plom_data["base_images"][i]["id"] = id_
        if md5 != plom_data["base_images"][i]["md5"]:
            log.warning("Plom file has wrong base image md5, replacing")
            plom_data["base_images"][i]["md5"] = md5
    return (True, plom_data, img_file)


def MgetOriginalImages(self, task):
    """Return the original (unannotated) page images of the given task to the user."""
    with plomdb.atomic():
        gref = Group.get_or_none(Group.gid == task)
        if gref is None:  # should not happen
            log.info("MgetOriginalImages - task %s not known", task)
            return (False, f"Task {task} not known")
        if not gref.scanned:
            log.warning("MgetOriginalImages - task %s not completely scanned", task)
            return (False, f"Task {task} is not completely scanned")
        # get the first non-outdated annotation for the group
        aref = (
            gref.qgroups[0]
            .annotations.where(Annotation.outdated == False)  # noqa: E712
            .order_by(Annotation.edition)
            .get()
        )
        # this is the earliest non-outdated annotation = the original

        rval = []
        for p in aref.apages.order_by(APage.order):
            rval.append(p.image.file_name)
        return (True, rval)


def MgetWholePaper(self, test_number, question):
    """Send page images of whole paper back to user, highlighting which belong to the given question. Do not show ID pages."""

    # we can show show not totally scanned test.
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:  # don't know that test - this shouldn't happen
        return [False]
    pageData = []  # for each page append a 4-tuple [
    # page-code = t.pageNumber, h.questionNumber.order, 3.questionNumber.order, or l.order
    # image-md5sum,
    # true/false - if belongs to the given question or not.
    # position in current annotation (or none if not)
    pageFiles = []  # the corresponding filenames.
    question = int(question)
    if question == 0:
        # Issue #1549: Identifier uses special question=0, but we need an aref below
        # TODO: for now we just get question 1 instead...
        qref = QGroup.get_or_none(test=tref, question=1)
    else:
        # get the current annotation and position of images within it.
        qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # this should not happen
        return [False]
    # dict of image-ids and positions in the current annotation
    current_image_orders = {}
    aref = qref.annotations[-1]
    if aref.apages.count() == 0:
        # this should never happen (?) no such thing as a "fresh annotation" any more
        log.critical("Oh my, colin thought it cannot happen aref={}".format(aref))
        raise RuntimeError("Oh my, colin thought it cannot happen")
        # return [False]
    for pref in aref.apages:
        current_image_orders[pref.image.id] = pref.order
    # give TPages (aside from ID pages), then HWPages, then EXPages
    for p in tref.tpages.order_by(TPage.page_number):
        if not p.scanned:  # skip unscanned testpages
            continue
        # skip IDpages (but we'll include dnm pages)
        if p.group.group_type == "i":
            continue
        val = [
            "t{}".format(p.page_number),
            p.image.md5sum,
            False,
            current_image_orders.get(p.image.id),
            p.image.id,
        ]
        # check if page belongs to our question
        if p.group.group_type == "q" and p.group.qgroups[0].question == question:
            val[2] = True
        pageData.append(val)
        pageFiles.append(p.image.file_name)
    # give HW and EX pages by question
    for qref in tref.qgroups.order_by(QGroup.question):
        for p in qref.group.hwpages:
            val = [
                "h{}.{}".format(qref.question, p.order),
                p.image.md5sum,
                False,
                current_image_orders.get(p.image.id),
                p.image.id,
            ]
            if qref.question == question:  # check if page belongs to our question
                val[2] = True
            pageData.append(val)
            pageFiles.append(p.image.file_name)
        for p in qref.group.expages:
            val = [
                "e{}.{}".format(qref.question, p.order),
                p.image.md5sum,
                False,
                current_image_orders.get(p.image.id),
                p.image.id,
            ]
            if qref.question == question:  # check if page belongs to our question
                val[2] = True
            pageData.append(val)
            pageFiles.append(p.image.file_name)
    return [True, pageData] + pageFiles


def MreviewQuestion(self, test_number, question, version):
    """Give ownership of the given marking task to the reviewer."""
    # shift ownership to "reviewer"
    revref = User.get(name="reviewer")  # should always be there

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    qref = QGroup.get_or_none(
        QGroup.test == tref,
        QGroup.question == question,
        QGroup.version == version,
        QGroup.marked == True,  # noqa: E712
    )
    if qref is None:
        return [False]
    with plomdb.atomic():
        qref.user = revref
        qref.time = datetime.now()
        qref.save()
    log.info("Setting tqv {}.{}.{} for reviewer".format(test_number, question, version))
    return [True]


def MrevertTask(self, task):
    """This needs work. The qgroup is set back to its original state, the annotations (and images) are deleted, and the corresponding to-delete-filenames are returned to the server which does the actual deleting of files. In future we should probably not delete any files and just move the references within the system?"""
    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        return [False, "NST"]  # no such task
    # from the group get the test and question - all need cleaning.
    qref = gref.qgroups[0]
    tref = gref.test
    # check task is "done"
    if qref.status != "done" or not qref.marked:
        return [False, "NAC"]  # nothing to do here
    # now update things
    log.info("Manager reverting task {}".format(task))
    with plomdb.atomic():
        # clean up test
        tref.marked = False
        tref.save()
        # clean up the qgroup
        qref.marked = False
        qref.status = "todo"
        qref.time = datetime.now()
        qref.user = None
        qref.save()
    # now we need to set annotations to "outdated"
    # first find the first not-outdated annotation - that is the "original" state
    aref0 = (
        gref.qgroups[0]
        .annotations.where(Annotation.outdated == False)  # noqa: E712
        .order_by(Annotation.edition)
        .get()
    )
    # now set all subsequent annotations to outdated
    for aref in gref.qgroups[0].annotations.where(
        Annotation.outdated == False, Annotation.edition > aref0.edition  # noqa: E712
    ):
        aref.outdated = True
        aref.save()

    log.info(f"Reverted tq {task}")
    return [True]


# ===== tag stuff


def McreateNewTag(self, user_name, tag_text):
    """Create a new tag entry in the DB

    Args:
        user_name (str): name of user creating the tag
        tag_text (str): the text of the tag - already validated by system

    Returns:
        tuple: `(True, key)` or `(False, err_msg)` where `key` is the
            key for the new tag.  Can fail if tag text is not alphanum, or if tag already exists.
    """
    if Tag.get_or_none(text=tag_text) is not None:
        return (False, "Tag already exists")

    uref = User.get(name=user_name)  # authenticated, so not-None
    with plomdb.atomic():
        # build unique key while holding atomic access
        # use a 10digit key to distinguish from rubrics
        key = generate_new_comment_ID(10)
        while Tag.get_or_none(key=key) is not None:
            key = generate_new_comment_ID(10)
        Tag.create(key=key, user=uref, creationTime=datetime.now(), text=tag_text)
    return (True, key)


def MgetAllTags(self):
    """Return a list of all tags - each tag is pair (key, text)"""
    # return all the tags
    tag_list = []
    for tref in Tag.select():
        tag_list.append((tref.key, tref.text))
    return tag_list


def McheckTagKeyExists(self, tag_key):
    """Check that the given tag_key in the database"""
    if Tag.get_or_none(key=tag_key) is None:
        return False
    else:
        return True


def McheckTagTextExists(self, tag_text):
    """Check that the given tag_text in the database"""
    if Tag.get_or_none(text=tag_text) is None:
        return False
    else:
        return True


def MgetTagsOfTask(self, task):
    """Get tags on given task.

    Returns:
        str/None: If no such task, return None.
    """

    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        log.error("MgetTags - task {} not known".format(task))
        return None
    qref = gref.qgroups[0]

    return [qtref.tag.text for qtref in qref.questiontaglinks]


def MaddExistingTag(self, username, task, tag_text):
    """Add an existing tag to the task"""
    uref = User.get(name=username)  # authenticated, so not-None

    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        log.error("MaddExistingTag - task {} not known".format(task))
        return False
    # get the question-group and the tag
    qref = gref.qgroups[0]
    tgref = Tag.get(text=tag_text)
    if tgref is None:
        # server existence of tag before, so this should not happen.
        log.warn(f"MaddExistingTag - tag {tag_text} is not in the system.")
        return False
    qtref = QuestionTagLink.get_or_none(qgroup=qref, tag=tgref)
    # check if task is already tagged
    if qtref is not None:
        log.warn(f"MaddExistingTag - task {task} is already tagged with {tag_text}.")
        return False
    else:
        QuestionTagLink.create(tag=tgref, qgroup=qref, user=uref)
        log.info(f"MaddExistingTag - tag {tag_text} added to task {task}.")
        return True


def MremoveExistingTag(self, task, tag_text):
    """Remove an existing tag to the task"""
    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        log.error("MremoveExistingTag - task {} not known".format(task))
        return False
    # get the question-group and the tag
    qref = gref.qgroups[0]
    tgref = Tag.get(text=tag_text)
    if tgref is None:
        # server existence of tag before, so this should not happen.
        log.warn(f"MaddExistingTag - tag {tag_text} is not in the system.")
        return False
    qtref = QuestionTagLink.get_or_none(qgroup=qref, tag=tgref)
    # check if task is already tagged
    if qtref is not None:
        qtref.delete_instance()
        log.info(f"MremoveExistingTag - tag {tag_text} removed from task {task}.")
        return True
    else:
        log.warn(f"MremoveExistingTag - task {task} did not have tag {tag_text}.")
        return False

    ##
    if qtref is not None:
        qtref.delete_instance()
        log.info(f"MremoveExistingTag - tag {tag_text} removed from task {task}.")
        return True
    else:
        log.warn(f"MremoveExistingTag - task {task} did not have tag {tag_text}.")
        return False


##
