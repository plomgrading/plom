# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2022 Joey Shi

from pathlib import Path
import logging

from plom.db.tables import UnknownPage, DiscardedPage, CollidingPage
from plom.db.tables import EXPage, HWPage, Image, QGroup, Test, TPage


log = logging.getLogger("DB")


def getUnknownPages(self):
    """Get information about the unknown pages

    Returns:
        list: each entry is dict of information about an unknown page.
        Keys include ``server_path``, ``orientation``, ``bundle_name``,
        ``bundle_position``, ``md5sum``, ``id``.
    """
    rval = []
    for uref in UnknownPage.select():
        rval.append(
            {
                "pagename": Path(uref.image.file_name).stem,
                "md5sum": uref.image.md5sum,
                "orientation": uref.image.rotation,
                "id": uref.image.id,
                "server_path": uref.image.file_name,
                "original_name": uref.image.original_name,
                "bundle_name": uref.image.bundle.name,
                "bundle_position": uref.order,  # same as uref.image.bundle_order?
            }
        )
    return rval


def getDiscardedPages(self):
    """Get information about the discarded pages

    Returns:
        list: each entry is dict of information about an unknown page.
        Keys include ``server_path``, ``orientation``, ``bundle_name``,
        ``bundle_position``, ``md5sum``, ``id``, and ``reason``.
    """
    pages = []
    for r in DiscardedPage.select():
        pages.append(
            {
                "pagename": Path(r.image.file_name).stem,
                "md5sum": r.image.md5sum,
                "orientation": r.image.rotation,
                "id": r.image.id,
                "server_path": r.image.file_name,
                "original_name": r.image.original_name,
                "bundle_name": r.image.bundle.name,
                "bundle_position": r.image.bundle_order,
                "reason": r.reason,
            }
        )
    return pages


def getCollidingPageNames(self):
    rval = {}
    for cref in CollidingPage.select():
        rval[cref.image.file_name] = [
            cref.tpage.test.test_number,
            cref.tpage.page_number,
            cref.tpage.version,
        ]
    return rval


def getTPageImage(self, test_number, page_number, version):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Paper {test_number} not found")
    p = TPage.get_or_none(
        TPage.test == tref,
        TPage.page_number == page_number,
        TPage.version == version,
    )
    if p is None:
        return (
            False,
            f"Cannot find page {page_number} version {version} in paper {test_number}",
        )
    return (
        True,
        [
            "t{}".format(p.page_number),
            p.image.md5sum,
            p.image.rotation,
            p.image.id,
            p.image.file_name,
        ],
    )


def getHWPageImage(self, test_number, question, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Paper {test_number} not found")
    gref = QGroup.get(test=tref, question=question).group
    p = HWPage.get_or_none(
        HWPage.test == tref, HWPage.group == gref, HWPage.order == order
    )
    if p is None:
        return (
            False,
            f"Cannot find homework page question {question} order {order} in paper {test_number}",
        )
    return (
        True,
        [
            "h{}.{}".format(question, p.order),
            p.image.md5sum,
            p.image.rotation,
            p.image.id,
            p.image.file_name,
        ],
    )


def getEXPageImage(self, test_number, question, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Paper {test_number} not found")
    gref = QGroup.get(test=tref, question=question).group
    p = EXPage.get_or_none(
        EXPage.test == tref, EXPage.group == gref, EXPage.order == order
    )
    if p is None:
        return (
            False,
            f"Cannot find extra page question {question} order {order} in paper {test_number}",
        )
    return (
        True,
        [
            "e{}.{}".format(question, p.order),
            p.image.md5sum,
            p.image.rotation,
            p.image.id,
            p.image.file_name,
        ],
    )


def getAllTestImages(self, test_number):
    """All pages in this paper included ID pages.

    Returns:
        tuple: `(True, rval)` on success or `(False, msg)` on failure.
        Here `msg` is an error message and `rval` is a list of lists
        where each inner "row" consists of:
        `[name, md5sum, id, orientation, server_path]`.
    """
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Cannot find paper {test_number}")

    # give the pages as IDPages, DNMPages and then for each question
    rval = []
    # grab the id group - only has tpages
    gref = tref.idgroups[0].group
    # give tpages if scanned.
    for p in gref.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(
                [
                    "id{}".format(p.page_number),
                    p.image.md5sum,
                    p.image.rotation,
                    p.image.id,
                    p.image.file_name,
                ]
            )

    # grab the dnm group - only has tpages
    gref = tref.dnmgroups[0].group
    # give tpages if scanned.
    for p in gref.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(
                [
                    "dnm{}".format(p.page_number),
                    p.image.md5sum,
                    p.image.rotation,
                    p.image.id,
                    p.image.file_name,
                ]
            )

    # for each question give TPages, HWPages and EXPages
    for qref in tref.qgroups.order_by(QGroup.question):
        gref = qref.group
        for p in gref.tpages.order_by(TPage.page_number):
            if p.scanned:
                rval.append(
                    [
                        "t{}".format(p.page_number),
                        p.image.md5sum,
                        p.image.rotation,
                        p.image.id,
                        p.image.file_name,
                    ]
                )
        for p in gref.hwpages.order_by(HWPage.order):
            rval.append(
                [
                    "h{}.{}".format(qref.question, p.order),
                    p.image.md5sum,
                    p.image.rotation,
                    p.image.id,
                    p.image.file_name,
                ]
            )
        for p in gref.expages.order_by(EXPage.order):
            rval.append(
                [
                    "e{}.{}".format(qref.question, p.order),
                    p.image.md5sum,
                    p.image.rotation,
                    p.image.id,
                    p.image.file_name,
                ]
            )

    return (True, rval)


def getQuestionImages(self, test_number, question):
    """All pages in this paper and this question.

    Returns:
        tuple: `(True, rval)` on success or `(False, msg)` on failure.
        Here `msg` is an error message and `rval` is a list of lists
        where each inner "row" consists of:
        `name`, `md5sum`, `id`, `orientation`, `server_path`
    """

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, f"Cannot find paper {test_number}")

    qref = QGroup.get_or_none(QGroup.test == tref, QGroup.question == question)
    if qref is None:
        return (False, f"Cannot find paper {test_number} question {question}")
    rval = []
    # append tpages, hwpages and expages
    for p in qref.group.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(
                [
                    "t{}".format(p.page_number),
                    p.image.md5sum,
                    p.image.rotation,
                    p.image.id,
                    p.image.file_name,
                ]
            )
    for p in qref.group.hwpages.order_by(HWPage.order):
        rval.append(
            [
                "h{}.{}".format(qref.question, p.order),
                p.image.md5sum,
                p.image.rotation,
                p.image.id,
                p.image.file_name,
            ]
        )
    for p in qref.group.expages.order_by(EXPage.order):
        rval.append(
            [
                "e{}.{}".format(qref.question, p.order),
                p.image.md5sum,
                p.image.rotation,
                p.image.id,
                p.image.file_name,
            ]
        )

    return (True, rval)


def testOwnersLoggedIn(self, tref):
    """Returns list of logged in users who own tasks in given test.

    Note - 'manager' and 'HAL' are not included in this list - else manager could block manager.
    """
    # make list of users who own tasks in the test (might have dupes and 'None')
    user_list = [qref.user for qref in tref.qgroups]
    user_list.append(tref.idgroups[0].user)

    logged_in_list = []
    for uref in user_list:
        if uref:  # make sure uref is not none.
            # avoid adding HAL or manager or duplicates
            if uref.name in ["HAL", "manager"] or uref.name in logged_in_list:
                continue
            if uref.token:
                logged_in_list.append(uref.name)
    return logged_in_list


def moveUnknownToExtraPage(self, file_name, test_number, questions):
    """Map an unknown page onto an extra page.

    args:
        file_name (str): a path and filename to a an image, e.g.,
            "pages/unknownPages/unk.16d85240.jpg"
        test_number (int):
        questions (list): list of ints to map this page onto.

    returns:
        tuple: a 3-tuple, either (True, None, None) if the action worked
        or `(False, code, msg)` where code is a short string, which
        currently can be "notfound", or "unscanned" and
        `msg` is a human-readable string suitable for an error message.
    """
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, "notfound", f"Cannot find image {file_name}")
    uref = iref.upages[0]
    if uref is None:
        return (False, "notfound", f"There is no UnknownPage with image {file_name}")

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "notfound", f"Cannot find test {test_number}")

    qref_list = []
    fails = []
    for question in questions:
        qref = QGroup.get_or_none(test=tref, question=question)
        if qref is None:
            fails.append(question)
        else:
            qref_list.append(qref)
    if fails:
        failed_questions = ", ".join(str(q) for q in fails)
        return (False, "notfound", f"Cannot find question(s) {failed_questions}")

    fails = []
    for question, qref in zip(questions, qref_list):
        # TODO: we may want to relax this restriction later, Issue #1900 et al
        if not qref.group.scanned:
            fails.append(question)
    if fails:
        if len(fails) == 1:
            is_are = "that question is"
        else:
            is_are = "those questions are"
        failed_questions = ", ".join(str(q) for q in fails)
        msg = f"Cannot attach extra page to test {test_number}, question "
        msg += f"{failed_questions} b/c {is_are} missing pages. "
        msg += "You must upload all Test Pages of a question "
        msg += "(or at least one HW Page) before adding extra pages."
        return (False, "unscanned", msg)

    with self._db.atomic():
        groups_to_update = self.get_groups_using_image(iref)
        for question, qref in zip(questions, qref_list):
            version = qref.version
            # find the last expage in that group - if there are expages
            if qref.group.expages.count() == 0:
                order = 1
            else:
                order = (
                    EXPage.select()
                    .where(EXPage.group == qref.group)
                    .order_by(EXPage.order.desc())
                    .get()
                    .order
                    + 1
                )

            EXPage.create(
                test=tref, group=qref.group, version=version, order=order, image=iref
            )
            log.info(
                "Moving unknown page %s to extra page %s of test %s question %s",
                file_name,
                order,
                test_number,
                question,
            )
            groups_to_update.add(qref.group)
        log.info("Removing %s from UnknownPages", file_name)
        uref.delete_instance()
    # update the groups containing the new extra-pages
    self.updateTestAfterChange(tref, group_refs=groups_to_update)
    return (True, None, None)


def moveUnknownToHWPage(self, file_name, test_number, questions):
    """Map an unknown page onto an extra page.

    args:
        file_name (str): a path and filename to a an image, e.g.,
            "pages/unknownPages/unk.16d85240.jpg"
        test_number (int):
        questions (list): a list of ints.

    returns:
        tuple: a 3-tuple, either `(True, None, None)` if the action worked
        or `(False, code, msg)` where `code` is a short string, which
        currently can be "notfound", and `msg` is a
        human-readable string suitable for an error message.
    """
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, "notfound", f"Cannot find image {file_name}")
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return (False, "notfound", f"There is no UnknownPage with image {file_name}")

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "notfound", f"Cannot find test {test_number}")

    qref_list = []
    fails = []
    for question in questions:
        qref = QGroup.get_or_none(test=tref, question=question)
        if qref is None:
            fails.append(question)
        else:
            qref_list.append(qref)
    if fails:
        failed_questions = ", ".join(str(q) for q in fails)
        return (False, "notfound", f"Cannot find question(s) {failed_questions}")

    with self._db.atomic():
        groups_to_update = self.get_groups_using_image(iref)
        for question, qref in zip(questions, qref_list):
            # find the last expage in that group - if there are expages
            if qref.group.hwpages.count() == 0:
                order = 1
            else:
                pref = (
                    HWPage.select()
                    .where(HWPage.group == qref.group)
                    .order_by(HWPage.order.desc())
                    .get()  # there will be at least one
                )
                order = pref.order + 1

            pref = self.createNewHWPage(tref, qref, order, iref)
            log.info(
                "Moving unknown page %s to HW page %s of test %s question %s",
                file_name,
                order,
                test_number,
                question,
            )
            groups_to_update.add(qref.group)
        log.info("Removing %s from UnknownPages", file_name)
        uref.delete_instance()
    # update groups associated to the image and new HW pages
    self.updateTestAfterChange(tref, group_refs=groups_to_update)
    return (True, None, None)


def moveUnknownToTPage(self, file_name, test_number, page_number):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, "notfound", f"Cannot find image {file_name}")
    uref = iref.upages[0]
    if uref is None:
        return (False, "notfound", f"There is no UnknownPage with image {file_name}")

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "notfound", f"Cannot find test {test_number}")

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:
        return (False, "notfound", f"Cannot find p.{page_number} of test {test_number}")

    if pref.scanned:
        return (
            False,
            "scanned",
            f"Page {page_number} of test {page_number} is already scanned",
        )

    self.attachImageToTPage(tref, pref, iref)
    uref.delete_instance()
    log.info(
        "Moving unknown page {} to page {} of test {}".format(
            file_name, page_number, test_number
        )
    )
    # update groups associated with the page and image
    groups_to_update = self.get_groups_using_image(iref)
    groups_to_update.add(pref.group)
    self.updateTestAfterChange(tref, group_refs=groups_to_update)

    return (True, None, None)


def checkTPage(self, test_number, page_number):
    """Check whether or not the test/page has been scanned.
    If so then return [collision message, version, image filename]
    Else return [unscanned message, version]
    """
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "no such test"]

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:
        return [False, "no such page"]
    if pref.scanned:  # we have a collision
        return [True, "collision", pref.version, pref.image.file_name]
    else:  # no collision since the page hasn't been scanned yet
        return [True, "unscanned", pref.version]


def removeUnknownImage(self, file_name, reason):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, f"Cannot find image {file_name}")
    uref = iref.upages[0]
    if uref is None:
        return (False, f"Cannot find unknown page for image {file_name}")

    if not reason:
        reason = "User discarded unknown page"
    with self._db.atomic():
        DiscardedPage.create(image=iref, reason=reason)
        uref.delete_instance()
    log.info('Discarding unknown image %s with reason "%s"', file_name, reason)
    return (True, None)


def moveDiscardToUnknown(self, file_name):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        log.warning("Tried to rescue non-existent discarded image %s", file_name)
        return (False, "Cannot find image")
    dref = iref.discards[0]
    if dref is None:
        log.warning("Tried to rescue non-existent discarded image %s", file_name)
        return (False, "Cannot find discard page for that image.")

    with self._db.atomic():
        # we have lost order information.
        UnknownPage.create(image=iref, order=1)
        dref.delete_instance()
    log.info("Moving discarded image %s to unknown image", file_name)
    return (True, None)


def moveUnknownToCollision(self, file_name, test_number, page_number):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, "notfound", f"Cannot find image {file_name}")
    uref = iref.upages[0]
    if uref is None:
        return (False, "notfound", f"There is no UnknownPage with image {file_name}")

    # find the test and the tpage
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "notfound", f"Cannot find test {test_number}")

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:
        return (False, "notfound", f"Cannot find p.{page_number} of test {test_number}")
    with self._db.atomic():
        CollidingPage.create(image=iref, tpage=pref)
        uref.delete_instance()
    log.info(
        "Moving unknown {} to collision of tp {}.{}".format(
            file_name, test_number, page_number
        )
    )
    return (True, None, None)


def getCollidingImage(self, file_name):
    # this really just confirms that the file_name belongs to an collidingpage
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return [False]
    cref = iref.collisions[0]
    if cref is None:
        return [False]
    else:
        return [True, cref.image.file_name]


def removeCollidingImage(self, file_name):
    # this really just confirms that the file_name belongs to an collidingpage
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return [False]
    cref = iref.collisions[0]
    if cref is None:
        return [False]

    pref = cref.tpage

    with self._db.atomic():
        DiscardedPage.create(
            image=iref,
            reason="Removed collision with {}.{}".format(
                pref.test.test_number, pref.page_number
            ),
        )
        cref.delete_instance()
    log.info(
        "Removing collision {} with {}.{}".format(
            file_name, pref.test.test_number, pref.page_number
        )
    )
    return [True]


def moveCollidingToTPage(self, file_name, test_number, page_number, version):
    """Move the collision into a TPage and move the original TPage to discards.

    return:
        3-tuple: `(True, None, None)`, or `(status, code, error_msg)`
        where the last field is human-readable.
    """
    # this really just confirms that the file_name belongs to an collidingpage
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return (False, "notfound", f"Cannot find image {file_name}")
    cref = iref.collisions[0]
    if cref is None:
        return (False, "notfound", f"Cannot find collision with name {file_name}")

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return (False, "notfound", f"Cannot find test {test_number}")

    pref = TPage.get_or_none(
        TPage.test == tref, TPage.page_number == page_number, TPage.version == version
    )
    if pref is None:
        return (False, "notfound", f"Cannot find p.{page_number} of test {test_number}")
    oref = pref.image  # the original page image for this tpage.

    # now create a discardpage with oref, and put iref into the tpage, delete the collision.
    with self._db.atomic():
        DiscardedPage.create(
            image=oref,
            reason="Replaced original image {} of {}.{} with new {}".format(
                file_name, pref.test.test_number, pref.page_number, oref.file_name
            ),
        )
        pref.image = iref
        pref.save()
        cref.delete_instance()
    log.info(
        "Collision {} replacing tpv {}.{}.{}".format(
            file_name, test_number, page_number, version
        )
    )

    # Update the group to which this new tpage officially belongs, but also look to see if it had been
    # attached to any annotations, in which case update those too.
    groups_to_update = self.get_groups_using_image(iref)
    groups_to_update.add(pref.group)
    self.updateTestAfterChange(tref, group_refs=groups_to_update)

    return (True, None, None)
