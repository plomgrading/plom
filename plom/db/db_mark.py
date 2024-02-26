# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022, 2024 Colin B. Macdonald
# Copyright (C) 2022 Joey Shi
# Copyright (C) 2022 Chris Jin

from datetime import datetime, timezone
import json
import logging
from time import time
import uuid

import peewee as pw

from plom.db.tables import AImage, Annotation, APage, ARLink
from plom.db.tables import (
    Image,
    Group,
    QGroup,
    Rubric,
    Test,
    TPage,
    HWPage,
    EXPage,
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


def MgetNextTask(self, q, v, *, tag, above):
    """Find unmarked (but scanned) q/v-group and send the group-id back to client."""
    with self._db.atomic():
        try:
            t0 = time()
            query = (
                QGroup.select()
                .join(Group)
                .where(
                    QGroup.status == "todo",
                    QGroup.question == q,
                    QGroup.version == v,
                    Group.scanned == True,  # noqa: E712
                    # QGroup.tag == tag,  # HELP!!
                    # QGroup.questiontaglink == tag,  # HELP!!
                )
            )
            t1 = time()
            if tag or above:
                if tag:
                    log.info('We are looking for tag "%s"', tag)
                # TODO: can't we SQL query it above without looping?
                for qref in query:
                    if tag:
                        tag_list = [qtref.tag.text for qtref in qref.questiontaglinks]
                        if tag in tag_list:
                            log.debug(f"we got tag match for '{tag}' in {tag_list}")
                            break
                    if above and qref.test.test_number >= above:
                        log.debug(f"we got match with paper_num >= {above}")
                        break
                else:
                    qref = query.get()
            else:
                qref = query.get()
            t2 = time()
            # as per #1811 - the user should be none here - assert here.
            assert (
                qref.user is None
            ), f"Marking-task for test {qref.test.test_number}, question {q} version {v} is todo, but has a user = {qref.user.name}"
        except pw.DoesNotExist:
            log.info("Nothing left on Q{}v{} to-do pile".format(q, v))
            return None

        task = qref.group.gid
        if tag or above:
            tstr = "%.3gs initial query + %.3gs tag filter" % (t1 - t0, t2 - t1)
        else:
            tstr = "%.3gs initial query + %.3gs get" % (t1 - t0, t2 - t1)
        log.info(f"Next Q{q}v{v} task = {task}, time = {tstr}")
        return task


def MgiveTaskToClient(self, user_name, group_id, version):
    """Assign a marking task to a certain user, and give them back needed data.

    args:
        user_name (str): the user name who is claiming the task.
        group_id (str): a "task code" like ``"q0020g3"``
        version (int): version requested - must match that in db.

    Return:
        list: On error, `[False, code, errmsg]` where `code` is a string:
        ``"other_claimed"``, ``"not_known"``, ``"not_scanned"``,
        ``"unexpected"``, ``"mismatch"``
        and `errmsg` is a human-readable error message.

        On success, the list is
        `[True, metadata, [list of tag texts], integrity_check]`
        where each row of `metadata` consists of dicts with keys
        `id, `md5`, `included`, `order`, `server_path`, `orientation`.

        Note: `server_path` is implementation-dependent, could change
        without notice, etc.  Clients could use this to get hints for
        what to use for a local file name for example.

    question/version via group_id as a task to the given user, unless has been
    taken by another user.

    Create new annotation by copying the last one for that qdata - pages created when returned.
    """

    uref = User.get(name=user_name)  # authenticated, so not-None

    with self._db.atomic():
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
        qref.time = datetime.now(timezone.utc)
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
            # See MgetWholePaper: somehow very similar :(
            # "pagename": "t{}".format(p.page_number) ?? ignore this?
            row = {
                "id": p.image.id,
                "md5": p.image.md5sum,
                "included": True,
                "order": p.order,
                "server_path": p.image.file_name,
                "orientation": p.image.rotation,
            }
            image_metadata.append(row)
        # update user activity
        uref.last_action = "Took M task {}".format(group_id)
        uref.last_activity = datetime.now(timezone.utc)
        uref.save()
        log.debug(
            'Giving marking task {} to user "{}" with integrity_check {}'.format(
                group_id, user_name, aref.integrity_check
            )
        )
        return [True, image_metadata, tag_list, aref.integrity_check]


def MgetOneImageRotation(self, image_id, md5):
    """Get the rotation of one image.

    Args:
        image_id: internal db ref number to image
        md5: the md5sum of that image (as sanity check)

    Returns:
        list: `[True, rotation]` or `[False, error_msg]` where
        `error_msg` is the string ``"no such image"`` or
        ``"wrong md5sum"``, and `rotation` is a float.
    """
    with self._db.atomic():
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
        return [True, iref.rotation]


def MgetOneImageFilename(self, image_id, md5):
    """Get the filename of one image.

    Args:
        image_id: internal db ref number to image
        md5: the md5sum of that image (as sanity check)

    Returns:
        list: `[True, file_name]` or `[False, error_msg]` where
        `error_msg` is the string ``"no such image"`` or
        ``"wrong md5sum"``, and `file_name` is a string.
    """
    with self._db.atomic():
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
    plom_json,
    rubrics,
    marking_time,
    md5,
    integrity_check,
    images_used,
):
    """Get marked image back from client and update the record
    in the database.
    Update the annotation.
    Check to see if all questions for that test are marked and if so update the test's 'marked' flag.
    """
    uref = User.get(name=user_name)  # authenticated, so not-None

    with self._db.atomic():
        # make sure all returned image-ids are actually images
        # keep the refs for apage creation
        image_ref_list = []
        for img in images_used:
            # img["md5"] is a sanity check here
            iref = Image.get_or_none(id=img["id"], md5sum=img["md5"])
            if iref is None:
                return [False, "No_such_image"]
            image_ref_list.append(iref)

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
        for img in images_used:
            if img["md5"] not in test_image_md5s:
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
            time=datetime.now(timezone.utc),
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
        qref.time = datetime.now(timezone.utc)
        qref.marked = True
        # the bundle for this image is given by the (fixed) bundle for the parent qgroup.
        aref.aimage = AImage.create(file_name=annot_fname, md5sum=md5)
        aref.mark = mark
        aref.plom_json = plom_json
        aref.marking_time = marking_time
        qref.save()
        aref.save()
        # update user activity
        uref.last_action = "Returned M task {}".format(task)
        uref.last_activity = datetime.now(timezone.utc)
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
        list: `[True, plom_json_data , annotation_image]` on success or
        on error `[False, error_msg]`.  If the task is not yet
        annotated, the error will be ``"no_such_task"``.
    """
    if edition is None:
        edition = -1
    edition = int(edition)
    task = f"q{number:04}g{question}"
    with self._db.atomic():
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

        img_file = aref.aimage.file_name

    plom_json = aref.plom_json
    plom_data = json.loads(plom_json)

    plom_data["user"] = aref.user.name
    plom_data["annotation_edition"] = aref.edition
    plom_data["annotation_reference"] = aref.id

    # Report any duplication in DB and plomfile (and keep DB version!)
    if plom_data["currentMark"] != aref.mark:
        log.warning("Plom file has wrong score, replacing")
        plom_data["currentMark"] = aref.mark
    for i, (id_, md5, _) in enumerate(metadata):
        if id_ != plom_data["base_images"][i]["id"]:
            log.error(
                "Plom file has wrong base image id %s, replacing with %s\ndata=%s",
                plom_data["base_images"][i]["id"],
                id_,
                plom_data,
            )
            plom_data["base_images"][i]["id"] = id_
        if md5 != plom_data["base_images"][i]["md5"]:
            log.error(
                "Plom file has wrong base image md5 %s, replacing with %s\ndata=%s",
                plom_data["base_images"][i]["md5"],
                md5,
                plom_data,
            )
            plom_data["base_images"][i]["md5"] = md5
    return (True, plom_data, img_file)


def MgetWholePaper(self, test_number, question):
    """All non-ID pages of a paper, highlighting which belong to a question.

    Returns:
        tuple: `(True, pagedata)` on success or `(False, msg)` on failure,
        where `msg` is an error message string when the test or question
        do not exist.  Here `pagedata` is a list of dict with
        keys `pagename`, `md5`, `id`, `orientation`, `server_path`,
        `order` and `included`.
        Note that pagedata could be an empty list when test paper exists
        but was never scanned or was deleted.
    """
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Paper {test_number} not found")

    pagedata = []
    question = int(question)
    # get the current annotation and position of images within it.
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:
        return (False, f"Cannot find paper {test_number} question {question}")
    # dict of image-ids and positions in the current annotation
    current_image_orders = {}
    aref = qref.annotations[-1]
    # if not scanned or discarded, there won't be any apages
    for pref in aref.apages:
        current_image_orders[pref.image.id] = pref.order

    # give TPages (aside from ID pages), then HWPages, then EXPages
    for p in tref.tpages.order_by(TPage.page_number):
        if not p.scanned:  # skip unscanned testpages
            continue
        # skip IDpages (but we'll include dnm pages)
        if p.group.group_type == "i":
            continue
        row = {
            "pagename": "t{}".format(p.page_number),
            "md5": p.image.md5sum,
            "included": False,
            "order": current_image_orders.get(p.image.id),
            "id": p.image.id,
            "server_path": p.image.file_name,
            "orientation": p.image.rotation,
        }
        # check if page belongs to our question
        if p.group.group_type == "q" and p.group.qgroups[0].question == question:
            row["included"] = True
        pagedata.append(row)

    # give HW and EX pages by question
    for qref in tref.qgroups.order_by(QGroup.question):
        for p in qref.group.hwpages:
            row = {
                "pagename": "h{}.{}".format(qref.question, p.order),
                "md5": p.image.md5sum,
                "included": False,
                "order": current_image_orders.get(p.image.id),
                "id": p.image.id,
                "server_path": p.image.file_name,
                "orientation": p.image.rotation,
            }
            if qref.question == question:  # check if page belongs to our question
                row["included"] = True
            pagedata.append(row)

        for p in qref.group.expages:
            row = {
                "pagename": "e{}.{}".format(qref.question, p.order),
                "md5": p.image.md5sum,
                "included": False,
                "order": current_image_orders.get(p.image.id),
                "id": p.image.id,
                "server_path": p.image.file_name,
                "orientation": p.image.rotation,
            }
            if qref.question == question:  # check if page belongs to our question
                row["included"] = True
            pagedata.append(row)
    return (True, pagedata)


def MreviewQuestion(self, test_number, question):
    """Give ownership of the given marking task to the reviewer.

    Returns:
        None

    Raises:
        ValueError: could not find paper or question.
        RuntimeError: no "reviewer" account.
    """
    revref = User.get_or_none(name="reviewer")

    if not revref:
        raise RuntimeError('There is no "reviewer" account')

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        raise ValueError(f"Could not find paper number {test_number}")
    qref = QGroup.get_or_none(
        QGroup.test == tref,
        QGroup.question == question,
        QGroup.marked == True,  # noqa: E712
    )
    version = qref.version
    if qref is None:
        raise ValueError(
            f"Could not find question {question} of paper number {test_number}"
        )
    with self._db.atomic():
        qref.user = revref
        qref.time = datetime.now(timezone.utc)
        qref.save()
    log.info("Setting tqv %s for reviewer", (test_number, question, version))


def MrevertTask(self, task):
    """Reset task, removing all annotations.

    Returns:
        list: `[bool, error_msg]` where `bool` is True on success
        and False on failure.  On failure, `error_msg` is string
        explanation appropriate for showing to users.
    """
    # This should be quite similar to the process of updating a qgroup after some changes in the underlying pages.
    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        return [False, f"Cannot find task {task}"]
    if gref.group_type != "q":
        return [False, f"Task {task} is not a marking task"]
    # get the test and qgroup associated with this group
    qref = gref.qgroups[0]
    tref = gref.test
    # get ref to HAL who will instantiate the new annotation
    HAL_ref = User.get(name="HAL")

    # reset all the qgroup info
    with self._db.atomic():
        # clean up the now-outdated annotations
        for aref in qref.annotations:
            aref.outdated = True
            aref.save()
        # now create a new latest annotation
        new_ed = qref.annotations[-1].edition + 1
        new_aref = Annotation.create(
            qgroup=qref,
            edition=new_ed,
            user=HAL_ref,
            time=datetime.now(timezone.utc),
        )
        # Add the relevant pages to the new annotation
        ord = 0
        for p in gref.tpages.order_by(TPage.page_number):
            if p.scanned:  # make sure the tpage is actually scanned.
                ord += 1
                APage.create(annotation=new_aref, image=p.image, order=ord)
        for p in gref.hwpages.order_by(HWPage.order):
            ord += 1
            APage.create(annotation=new_aref, image=p.image, order=ord)
        for p in gref.expages.order_by(EXPage.order):
            ord += 1
            APage.create(annotation=new_aref, image=p.image, order=ord)
        # set the integrity_check string to a UUID
        new_aref.integrity_check = uuid.uuid4().hex
        new_aref.save()
        # clean up the qgroup
        qref.status = "todo"
        qref.user = None
        qref.marked = False
        qref.time = datetime.now(timezone.utc)

        qref.save()
        # set the test as unmarked.
        tref.marked = False
        tref.save()
    # finally log it!
    log.info(f"Task {task} of test {tref.test_number} reverted.")
    return [True, None]


# ===== tag stuff


def McreateNewTag(self, user_name, tag_text):
    """Create a new tag entry in the DB

    Args:
        user_name (str): name of user creating the tag
        tag_text (str): the text of the tag - already validated by system

    Returns:
        tuple: `(True, key)` or `(False, err_msg)` where `key` is the
        key for the new tag.  Can fail if tag text is not alphanum, or
        if tag already exists.
    """
    if Tag.get_or_none(text=tag_text) is not None:
        return (False, "Tag already exists")

    uref = User.get(name=user_name)  # authenticated, so not-None
    with self._db.atomic():
        # build unique key while holding atomic access
        # use a 10digit key to distinguish from rubrics
        key = generate_new_comment_ID(10)
        while Tag.get_or_none(key=key) is not None:
            key = generate_new_comment_ID(10)
        Tag.create(
            key=key, user=uref, creationTime=datetime.now(timezone.utc), text=tag_text
        )
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
    """Add an existing tag to the task

    Returns:
        tuple: ``ok, errcode, msg``.
    """
    uref = User.get(name=username)  # authenticated, so not-None

    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        msg = f"task {task} not known"
        log.error(f"tag task: {msg}")
        return False, "notfound", msg
    # get the question-group and the tag
    qref = gref.qgroups[0]
    tgref = Tag.get(text=tag_text)
    if tgref is None:
        # server ensured existence of tag before, so this should not happen.
        msg = f"tag {tag_text} is not in the system"
        log.warning(f"tag task: {msg}")
        return False, "nosuchtag", msg
    qtref = QuestionTagLink.get_or_none(qgroup=qref, tag=tgref)
    # check if task is already tagged
    if qtref is not None:
        msg = f"task {task} is already tagged with {tag_text}"
        log.warning(f"tag task: {msg}")
        return False, "already", msg
    QuestionTagLink.create(tag=tgref, qgroup=qref, user=uref)
    log.info(f"tag {tag_text} added to task {task}.")
    return True, None, None


def MremoveExistingTag(self, task, tag_text):
    """Remove an existing tag from the task

    Args:
        task (str): Code string for the task (paper number and question).
        tag_text (str): Text of tag to remove.

    Returns:
        None

    Raises:
        ValueError: no such task.
        KeyError: no such tag.
    """
    gref = Group.get_or_none(Group.gid == task)
    if gref is None:
        log.error("MremoveTag - task %s not known", task)
        raise ValueError(f"No such task {task}")
    # get the question-group and the tag
    qref = gref.qgroups[0]
    tagref = Tag.get(text=tag_text)
    if tagref is None:
        log.warning('MremoveTag - tag "%s" is not in the system', tag_text)
        raise KeyError(f'The system has no such tag "{tag_text}"')
    qtref = QuestionTagLink.get_or_none(qgroup=qref, tag=tagref)
    if qtref is None:
        log.warning('MremoveTag - task %s does not have tag "%s"', task, tag_text)
        raise KeyError(f'Task {task} has no such tag "{tag_text}"')
    qtref.delete_instance()
    log.info('MremoveTag - tag "%s" removed from task %s', tag_text, task)
