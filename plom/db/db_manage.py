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


def getLPageImage(self, test_number, order):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    pref = LPage.get_or_none(LPage.test == tref, LPage.order == order)
    if pref is None:
        return [False]
    else:
        return [True, pref.image.file_name]


def getUnknownImage(self, fname):
    uref = UnknownPage.get_or_none(UnknownPage.file_name == fname)
    if uref is None:
        return [False]
    else:
        return [True, uref.file_name]


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


def getQuestionImages(self, test_number, question):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    qref = QGroup.get_or_none(QGroup.test == tref, QGroup.question == question)
    if qref is None:
        return [False]
    rval = [True]
    for p in qref.group.pages.order_by(Page.page_number):
        rval.append(p.file_name)
    return rval


def getTestImages(self, test_number):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    rval = [True]
    for p in tref.tpages.order_by(TPage.page_number):
        if p.scanned == True:
            rval.append(p.image.file_name)
    for p in tref.hwpages.order_by(HWPage.order):  # then give HWPages
        rval.append(p.image.file_name)
    for p in tref.lpages.order_by(LPage.order):  # then give LPages
        rval.append(p.image.file_name)

    return rval


def checkPage(self, test_number, page_number):
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    pref = Page.get_or_none(Page.test == tref, Page.page_number == page_number)
    if pref is None:
        return [False]
    if pref.scanned:  # we have a collision
        return [True, pref.version, pref.file_name]
    else:  # no collision since the page hasn't been scanned yet
        return [True, pref.version]


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


def moveUnknownToPage(self, fname, nname, test_number, page_number):
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
        pref.file_name = nname
        pref.md5sum = uref.md5sum
        pref.original_name = uref.original_name
        pref.scanned = True
        pref.save()
        uref.delete_instance()
    log.info(
        "Moving unknown {} to image {} of tp {}.{}".format(
            fname, nname, test_number, page_number
        )
    )
    self.checkGroupAllUploaded(pref)
    return [True]


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


def moveExtraToPage(self, fname, nname, test_number, question):
    uref = UnknownPage.get_or_none(UnknownPage.file_name == fname)
    if uref is None:
        return [False]
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False]
    # find the group to which the new page should belong
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:
        return [False]
    version = qref.version
    # get the last page in the test.
    pref = (
        Page.select().where(Page.test == tref).order_by(Page.page_number.desc()).get()
    )
    # extra pages start with page-number 1001
    nextpage_number = max(pref.page_number + 1, 1001)
    with plomdb.atomic():
        npref = Page.create(
            test=tref,
            group=qref.group,
            gid=qref.group.gid,
            page_number=nextpage_number,
            version=version,
            original_name=uref.original_name,
            file_name=nname,  # since the file is moved
            md5sum=uref.md5sum,
            scanned=True,
        )
        uref.delete_instance()
    log.info(
        "Saving extra {} as {} tp {}.{} of question {}".format(
            fname, nname, test_number, nextpage_number, questionNumber
        )
    )
    ## Now invalidate any work on the associated group
    # now update the group and keep list of files to delete potentially
    return [True, self.invalidateQGroup(tref, qref.group, delPage=False)]


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
