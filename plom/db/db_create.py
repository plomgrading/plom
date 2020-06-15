# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

from datetime import datetime
import logging

from peewee import fn
import peewee as pw

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName
from plom.db.tables import *

log = logging.getLogger("DB")


########## Test creation stuff ##############
def areAnyPapersProduced(self):
    """True if any papers have been produced."""
    return len(Test.select()) > 0


def nextqueue_position(self):
    lastPos = Group.select(fn.MAX(Group.queue_position)).scalar()
    if lastPos is None:
        return 0
    else:
        return lastPos + 1


def createTest(self, t):
    with plomdb.atomic():
        try:
            tref = Test.create(test_number=t)  # must be unique
            sref = SumData.create(test=tref)  # also create the sum-data
        except IntegrityError as e:
            log.error("Create test {} error - {}".format(t, e))
            return False
    return True


def addTPages(self, tref, gref, t, pages, v):
    """
    For initial construction of test-pages for a test. We use these so we know what structured pages we should have.
    """
    flag = True
    with plomdb.atomic():
        for p in pages:
            try:
                TPage.create(
                    test=tref, group=gref, page_number=p, version=v, scanned=False,
                )
            except IntegrityError as e:
                log.error("Adding page {} for test {} error - {}".format(p, t, e))
                flag = False
    return flag


def createIDGroup(self, t, pages):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        log.warning("Create IDGroup - No test with number {}".format(t))
        return False
    with plomdb.atomic():
        # make the Group
        gid = "i{}".format(str(t).zfill(4))
        try:
            gref = Group.create(
                test=tref,
                gid=gid,
                group_type="i",
                queue_position=self.nextqueue_position(),
            )  # must be unique
        except IntegrityError as e:
            log.error(
                "Create ID - cannot create Group {} of test {} error - {}".format(gid, t, e)
            )
            return False
        # make the IDGroup
        try:
            iref = IDGroup.create(test=tref, group=gref)
        except IntegrityError as e:
            log.error(
                "Create ID - cannot create IDGroup {} of group {} error - {}.".format(
                    qref, gref, e
                )
            )
            return False
        return self.addTPages(tref, gref, t, pages, 1)  # always version 1.


def createDNMGroup(self, t, pages):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        log.warning("Create DNM - No test with number {}".format(t))
        return False

    gid = "d{}".format(str(t).zfill(4))
    with plomdb.atomic():
        # make the dnmgroup
        try:
            # A DNM group may have 0 pages, in that case mark it as scanned and set status = "complete"
            sc = True if len(pages) == 0 else False
            gref = Group.create(
                test=tref,
                gid=gid,
                group_type="d",
                scanned=sc,
                queue_position=self.nextqueue_position(),
            )
        except IntegrityError as e:
            log.error(
                "Create DNM - cannot make Group {} of Test {} error - {}".format(gid, t, e)
            )
            return False
        try:
            dref = DNMGroup.create(test=tref, group=gref)
        except IntegrityError as e:
            log.error(
                "Create DNM - cannot create DNMGroup {} of group {} error - {}.".format(
                    dref, gref, e
                )
            )
            return False
        return self.addTPages(tref, gref, t, pages, 1)


def createQGroup(self, t, g, v, pages):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        log.warning("Create Q - No test with number {}".format(t))
        return False

    gid = "q{}g{}".format(str(t).zfill(4), g)
    with plomdb.atomic():
        # make the qgroup
        try:
            gref = Group.create(
                test=tref,
                gid=gid,
                group_type="q",
                version=v,
                queue_position=self.nextqueue_position(),
            )
        except IntegrityError as e:
            log.error(
                "Create Q - cannot create group {} of Test {} error - {}".format(gid, t, e)
            )
            return False
        try:
            qref = QGroup.create(test=tref, group=gref, question=g, version=v)
        except IntegrityError as e:
            log.error(
                "Create Q - cannot create QGroup of question {} error - {}.".format(gid, e)
            )
            return False
        ## create annotation 0 owned by HAL
        try:
            uref = User.get(name="HAL")
            aref = Annotation.create(qgroup=qref, edition=0, user=uref)
        except IntegrityError as e:
            log.error(
                "Create Q - cannot create Annotation  of question {} error - {}.".format(
                    gid, e
                )
            )
            return False

        return self.addTPages(tref, gref, t, pages, v)


def getPageVersions(self, t):
    """Get the mapping between page numbers and version for a test.

    Args:
        t (int): a paper number.

    Returns:
        dict: keys are page numbers (int) and value is the page
            version (int), or empty dict if there was no such paper.
    """
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        return {}
    else:
        pvDict = {p.page_number: p.version for p in tref.tpages}
        return pvDict


def produceTest(self, t):
    """Someone has told us they produced (made PDF) for this paper.

    Args:
        t (int): a paper number.

    Exceptions:
        IndexError: no such paper exists.
        ValueError: you already told us you made it.
    """
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        log.error('Cannot set paper {} to "produced" - it does not exist'.format(t))
        raise IndexError("Paper number does not exist: out of range?")
    else:
        # TODO - work out how to make this more efficient? Multiple updates in one op?
        with plomdb.atomic():
            if tref.produced:
                # TODO be less harsh if we have the same md5sum
                log.error('Paper {} was already "produced"!'.format(t))
                raise ValueError("Paper was already produced")
            tref.produced = True
            tref.save()
        log.info('Paper {} is set to "produced"'.format(t))
