from plom.db.tables import *

from datetime import datetime

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

import logging

log = logging.getLogger("DB")

from peewee import fn


def getUnknownPageNames(self):
    rval = []
    for uref in UnknownPage.select():
        rval.append(uref.image.file_name)
    return rval


def getDiscardNames(self):
    rval = []
    for dref in DiscardedPage.select():
        rval.append([dref.image.file_name, dref.reason])
    return rval


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
        return [False]
    pref = TPage.get_or_none(
        TPage.test == tref,
        TPage.page_number == page_number,
        TPage.version == version,
    )
    if pref is None:
        return [False]
    else:
        return [True, pref.image.file_name]


def getHWPageImage(self, test_number, question, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    gref = QGroup.get(test=tref, question=question).group
    pref = HWPage.get_or_none(
        HWPage.test == tref, HWPage.group == gref, HWPage.order == order
    )
    if pref is None:
        return [False]
    else:
        return [True, pref.image.file_name]


def getEXPageImage(self, test_number, question, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    gref = QGroup.get(test=tref, question=question).group
    pref = EXPage.get_or_none(
        EXPage.test == tref, EXPage.group == gref, EXPage.order == order
    )
    if pref is None:
        return [False]
    else:
        return [True, pref.image.file_name]


def getLPageImage(self, test_number, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    pref = LPage.get_or_none(LPage.test == tref, LPage.order == order)
    if pref is None:
        return [False]
    else:
        return [True, pref.image.file_name]


def getAllTestImages(self, test_number):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    rval = [True]

    # give the pages as IDPages, DNMPages and then for each question

    # grab the id group - only has tpages
    gref = tref.idgroups[0].group
    # give tpages if scanned.
    for p in gref.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(p.image.file_name)

    # grab the dnm group - only has tpages
    gref = tref.dnmgroups[0].group
    # give tpages if scanned.
    for p in gref.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(p.image.file_name)

    # for each question give TPages, HWPages and EXPages
    for qref in tref.qgroups.order_by(QGroup.question):
        gref = qref.group
        for p in gref.tpages.order_by(TPage.page_number):
            if p.scanned:
                rval.append(p.image.file_name)
        for p in gref.hwpages.order_by(HWPage.order):
            rval.append(p.image.file_name)
        for p in gref.expages.order_by(EXPage.order):
            rval.append(p.image.file_name)

    # finally give any loosepages
    for p in tref.lpages.order_by(LPage.order):
        rval.append(p.image.file_name)

    return rval


def getQuestionImages(self, test_number, question):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    qref = QGroup.get_or_none(QGroup.test == tref, QGroup.question == question)
    if qref is None:
        return [False]
    rval = [True]
    # append tpages, hwpages and expages
    for p in qref.group.tpages.order_by(TPage.page_number):
        if p.scanned:
            rval.append(p.image.file_name)
    for p in qref.group.hwpages.order_by(HWPage.order):
        rval.append(p.image.file_name)
    for p in qref.group.expages.order_by(EXPage.order):
        rval.append(p.image.file_name)
    return rval


def getUnknownImage(self, file_name):
    # this really just confirms that the file_name belongs to an unknmown
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return [False]
    uref = iref.upages[0]
    if uref is None:
        return [False]
    else:
        return [True, uref.image.file_name]


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


def moveUnknownToExtraPage(self, file_name, test_number, question):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return [False, "Cannot find unknown page for that image."]

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "Cannot find that test"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    # find the qgroup to which the new page should belong
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # should not happen
        return [False, "Cannot find that question"]
    version = qref.version  # we'll need the version
    gref = qref.group  # and the parent group
    # find the last expage in that group - if there are expages
    if gref.expages.count() == 0:
        order = 1
    else:
        pref = (
            EXPage.select()
            .where(EXPage.group == gref)
            .order_by(EXPage.order.desc())
            .get()
        )
        order = pref.order + 1

    # now create the expage, delete upage

    with plomdb.atomic():
        xref = EXPage.create(
            test=tref, group=qref.group, version=version, order=order, image=iref
        )
        uref.delete_instance()
        gref.recent_upload = True
        gref.save()
        log.info(
            "Moving unknown page {} to extra page {} of question {} of test {}".format(
                file_name, order, question, test_number
            )
        )
    self.updateTestAfterUpload(tref)
    return [True]


def moveUnknownToHWPage(self, file_name, test_number, question):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return [False, "Cannot find unknown page for that image."]

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "Cannot find that test"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    # find the qgroup to which the new page should belong
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # should not happen
        return [False, "Cannot find that question"]
    version = qref.version  # we'll need the version
    gref = qref.group  # and the parent group
    # find the last expage in that group - if there are expages
    if gref.hwpages.count() == 0:
        order = 1
    else:
        pref = (
            HWPage.select()
            .where(HWPage.group == gref)
            .order_by(HWPage.order.desc())
            .get()  # there will be at least one
        )
        order = pref.order + 1

    # now create the hwpage, delete upage
    self.createNewHWPage(tref, qref, order, iref)
    uref.delete_instance()
    log.info(
        "Moving unknown page {} to hw page {} of question {} of test {}".format(
            file_name, order, question, test_number
        )
    )
    self.updateTestAfterUpload(tref)
    return [True]


def moveUnknownToTPage(self, file_name, test_number, page_number):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return [False, "Cannot find unknown page for that image."]

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:  # should not happen
        return [False, "Cannot find that test"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:  # should not happen
        return [False, "Cannot find that page."]

    if pref.scanned:
        return [
            False,
            "Page {} of test {} is already scanned.".format(page_number, test_number),
        ]

    self.attachImageToTPage(tref, pref, iref)
    uref.delete_instance()
    log.info(
        "Moving unknown page {} to page {} of test {}".format(
            file_name, page_number, test_number
        )
    )
    self.updateTestAfterUpload(tref)

    return [True]


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


def removeUnknownImage(self, file_name):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return [False, "Cannot find unknown page for that image."]

    with plomdb.atomic():
        DiscardedPage.create(image=iref, reason="User discarded unknown page")
        uref.delete_instance()
    log.info("Discarding unknown image {}".format(file_name))
    return [True]


def getDiscardImage(self, file_name):
    # this really just confirms that the file_name belongs to an discard
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return [False]
    dref = iref.discards[0]
    if dref is None:
        return [False]
    else:
        return [True, dref.image.file_name]


def moveDiscardToUnknown(self, file_name):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    dref = iref.discards[0]
    if dref is None:  # should not happen
        return [False, "Cannot find discard page for that image."]

    with plomdb.atomic():
        UnknownPage.create(image=iref, order=1)  # we have lost order information.
        dref.delete_instance()
    log.info("Moving discarded image {} to unknown image".format(file_name))
    return [True]


def moveUnknownToCollision(self, file_name, test_number, page_number):
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:  # should not happen
        return [False, "Cannot find image"]
    uref = iref.upages[0]
    if uref is None:  # should not happen
        return [False, "Cannot find unknown page for that image."]

    # find the test and the tpage
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:
        return [False, "Cannot find that page"]
    with plomdb.atomic():
        CollidingPage.create(image=iref, tpage=pref)
        uref.delete_instance()
    log.info(
        "Moving unknown {} to collision of tp {}.{}".format(
            file_name, test_number, page_number
        )
    )
    return [True]


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

    with plomdb.atomic():
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
    # this really just confirms that the file_name belongs to an collidingpage
    iref = Image.get_or_none(file_name=file_name)
    if iref is None:
        return [False, "Cannot find image with name {}".format(file_name)]
    cref = iref.collisions[0]
    if cref is None:
        return [False, "Cannot find collision with name {}".format(file_name)]

    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "Cannot find test number {}".format(test_number)]

    pref = TPage.get_or_none(
        TPage.test == tref, TPage.page_number == page_number, TPage.version == version
    )
    if pref is None:
        return [
            False,
            "Cannot find page {} of test {}".format(page_number, test_number),
        ]
    oref = pref.image  # the original page image for this tpage.
    # get the group of that tpage - so we can trigger an update.
    gref = pref.group

    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    # now create a discardpage with oref, and put iref into the tpage, delete the collision.
    with plomdb.atomic():
        DiscardedPage.create(
            image=oref,
            reason="Replaced original image {} of {}.{} with new {}".format(
                file_name, pref.test.test_number, pref.page_number, oref.file_name
            ),
        )
        pref.image = iref
        pref.save()
        gref.recent_upload = True
        gref.save()
        cref.delete_instance()
    log.info(
        "Collision {} replacing tpv {}.{}.{}".format(
            file_name, test_number, page_number, version
        )
    )
    # trigger an update since underlying image changed.
    self.updateTestAfterUpload(tref)
    return [True]
