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
        rval.append(dref.image.file_name)
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
        TPage.test == tref, TPage.page_number == page_number, TPage.version == version,
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


def getExPageImage(self, test_number, question, order):
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
            .get_or_none()
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

    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:  # should not happen
        return [False, "Cannot find that page."]

    if pref.scanned:
        return [
            False,
            "Page {} of test {} is already scanned.".format(page_number, test_number),
        ]
    # get the group associated with that page
    gref = pref.group
    with plomdb.atomic():
        pref.image = iref
        pref.scanned = True
        pref.save()
        uref.delete_instance()
        gref.recent_upload = True
        gref.save()
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
        return [False]
    pref = TPage.get_or_none(TPage.test == tref, TPage.page_number == page_number)
    if pref is None:
        return [False]
    if pref.scanned:  # we have a collision
        return [True, "collision", pref.version, pref.image.file_name]
    else:  # no collision since the page hasn't been scanned yet
        return [True, "unscanned", pref.version]


# still need fixing up.


def getDiscardImage(self, fname):
    dref = DiscardedPage.get_or_none(DiscardedPage.file_name == fname)
    if dref is None:
        return [False]
    else:
        return [True, dref.file_name]


def getCollidingImage(self, fname):
    cref = CollidingPage.get_or_none(CollidingPage.file_name == fname)
    if cref is None:
        return [False]
    else:
        return [True, cref.file_name]


def checkUnknownImage(self, fname):
    uref = UnknownPage.get_or_none(UnknownPage.file_name == fname)
    if uref is None:
        return None
    return [uref.file_name, uref.original_name, uref.md5sum]


def checkCollidingImage(self, fname):
    cref = CollidingPage.get_or_none(CollidingPage.file_name == fname)
    if cref is None:
        return None
    return [cref.file_name, cref.original_name, cref.md5sum]


def removeUnknownImage(self, fname, nname):
    uref = UnknownPage.get_or_none(UnknownPage.file_name == fname)
    if uref is None:
        return False
    with plomdb.atomic():
        DiscardedPage.create(
            file_name=nname, original_name=uref.original_name, md5sum=uref.md5sum
        )
        uref.delete_instance()
    log.info("Removing unknown {} to discard {}".format(fname, nname))
    return True


def removeCollidingImage(self, fname, nname):
    cref = CollidingPage.get_or_none(file_name=fname)
    if cref is None:
        return False
    with plomdb.atomic():
        DiscardedPage.create(
            file_name=nname, original_name=cref.original_name, md5sum=cref.md5sum
        )
        cref.delete_instance()
    log.info("Removing collision {} to discard {}".format(fname, nname))
    return True


def moveUnknownToCollision(self, fname, nname, test_number, page_number):
    uref = UnknownPage.get_or_none(UnknownPage.file_name == fname)
    if uref is None:
        return [False]
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    pref = Page.get_or_none(Page.test == tref, Page.page_number == page_number)
    if pref is None:
        return [False]
    with plomdb.atomic():
        CollidingPage.create(
            page=pref,
            original_name=uref.original_name,
            file_name=nname,
            md5sum=uref.md5sum,
        )
        uref.delete_instance()
    log.info(
        "Moving unknown {} to collision {} of tp {}.{}".format(
            fname, nname, test_number, page_number
        )
    )
    return [True]


def moveCollidingToPage(self, fname, nname, test_number, page_number, version):
    cref = CollidingPage.get_or_none(CollidingPage.file_name == fname)
    if cref is None:
        return [False]
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    pref = Page.get_or_none(
        Page.test == tref, Page.page_number == page_number, Page.version == version
    )
    if pref is None:
        return [False]
    with plomdb.atomic():
        pref.file_name = nname
        pref.md5sum = cref.md5sum
        pref.original_name = cref.original_name
        pref.scanned = True
        pref.save()
        cref.delete_instance()
    log.info(
        "Collision {} replacing tpv {}.{}.{} as {}".format(
            fname, test_number, page_number, version, nname
        )
    )
    self.checkGroupAllUploaded(pref)
    return [True]


def moveDiscardToUnknown(self, fname, nname):
    dref = DiscardedPage.get_or_none(file_name=fname)
    if dref is None:
        return [False]
    with plomdb.atomic():
        uref = UnknownPage.create(
            original_name=dref.original_name, file_name=nname, md5sum=dref.md5sum
        )
        uref.save()
        dref.delete_instance()
    log.info("Moving discard {} back to unknown {}".format(fname, nname))
    return [True]
