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


########## Bundle creation ##########


def createReplacementBundle(self):
    try:
        bref = Bundle.create(name="replacements")
    except IntegrityError as e:
        log.error("Create replacement page bundle = {}.{} error - {}".format(e))
        return False
    return True


def doesBundleExist(self, bundle_name, md5):
    """
    Checks if bundle with name=bundle_name or md5sum=md5 exists.
    4 possibilities
    * neither = no matching bundle, return [False]
    * name but not md5 = return [True, 'name'] - user is trying to upload different bundles with same name.
    * md5 but not name = return [True, 'md5sum'] - user is trying to same bundle with different names.
    * both match = return [True, 'both'] - user could be retrying after
      network failure (for example) or uploading unknown or colliding
      pages.
    """
    # check if that bundle-name is on file, and if the md5sum is known.
    bref = Bundle.get_or_none(name=bundle_name)
    if bref is not None:
        if bref.md5sum == md5:
            # name and md5sum match one in system
            # probably a crash occurred, so also return all the bundle_orders known in this bundle
            skip_list = []
            for iref in bref.images:
                skip_list.append(iref.bundle_order)
            return [True, "both", skip_list]

        else:
            return [True, "name"]
    # name not known, so just check md5sum
    if Bundle.get_or_none(md5sum=md5) is not None:
        return [True, "md5sum"]
    return [False, "no such bundle"]


def createNewBundle(self, bundle_name, md5):
    """
    Checks to see if bundle exists using 'doesBundleExist'.
    If bundle matches either 'name' or 'md5sum' then return [False, reason] - this shouldnt happen if scanner working correctly.
    If bundle matches 'both' then return [True, skip_list] where skip_list = the page-orders from that bundle that are already in the system. The scan scripts will then skip those uploads.
    If no such bundle return [True, []] - create the bundle and return an empty skip-list.
    """
    # use the doesBundleExist command logic to sanity check
    bundle_check = self.doesBundleExist(bundle_name, md5)
    if bundle_check[0] is False:
        Bundle.create(name=bundle_name, md5sum=md5)
        return [True, []]
    elif bundle_check[1] == "both":  # return [True, skip-list]
        bref = Bundle.get_or_none(name=bundle_name, md5sum=md5)
        skip_list = []
        for iref in bref.images:
            skip_list.append(iref.bundle_order)
        return [True, skip_list]
    else:
        return [False, bundle_check[1]]


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
        except pw.IntegrityError as e:
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
                    test=tref,
                    group=gref,
                    page_number=p,
                    version=v,
                    scanned=False,
                )
            except pw.IntegrityError as e:
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
        except pw.IntegrityError as e:
            log.error(
                "Create ID - cannot create Group {} of test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        # make the IDGroup
        try:
            iref = IDGroup.create(test=tref, group=gref)
        except pw.IntegrityError as e:
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
        except pw.IntegrityError as e:
            log.error(
                "Create DNM - cannot make Group {} of Test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        try:
            dref = DNMGroup.create(test=tref, group=gref)
        except pw.IntegrityError as e:
            log.error(
                "Create DNM - cannot create DNMGroup {} of group {} error - {}.".format(
                    dref, gref, e
                )
            )
            return False
        return self.addTPages(tref, gref, t, pages, 1)


def createQGroup(self, t, q, v, pages):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        log.warning("Create Q - No test with number {}".format(t))
        return False

    gid = "q{}g{}".format(str(t).zfill(4), q)

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
        except pw.IntegrityError as e:
            log.error(
                "Create Q - cannot create group {} of Test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        try:
            qref = QGroup.create(test=tref, group=gref, question=q, version=v)
        except pw.IntegrityError as e:
            log.error(
                "Create Q - cannot create QGroup of question {} error - {}.".format(
                    gid, e
                )
            )
            return False
        ## create annotation 0 owned by HAL
        try:
            uref = User.get(name="HAL")
            aref = Annotation.create(qgroup=qref, edition=0, user=uref)
        except pw.IntegrityError as e:
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


def id_paper(self, paper_num, user_name, sid, sname):
    """Associate student name and id with a paper in the database.

    See also :func:`plom.db.db_identify.ID_id_paper` which is similar.

    Args:
        paper_num (int)
        user_name (str): User who did the IDing.
        sid (str): student id.
        sname (str): student name.

    Returns:
        tuple: `(True, None, None)` if succesful, `(False, 409, msg)`
            means `sid` is in use elsewhere, a serious problem for
            the caller to deal with.  `(False, int, msg)` covers all
            other errors.  `msg` gives details about errors.  Some
            of these should not occur, and indicate possible bugs.
            `int` gives a hint of suggested HTTP status code,
            currently it can be 404 or 409.

    TODO: perhaps several sorts of exceptions would be better.
    """
    uref = User.get(name=user_name)  # TODO: or hardcode HAL like before
    # since user authenticated, this will always return legit ref.

    logbase = 'User "{}" tried to ID paper {}'.format(user_name, paper_num)
    with plomdb.atomic():
        tref = Test.get_or_none(Test.test_number == paper_num)
        if tref is None:
            msg = "denied b/c paper not found"
            log.error("{}: {}".format(logbase, msg))
            return False, 404, msg
        iref = tref.idgroups[0]
        iref.user = uref
        iref.status = "done"
        iref.student_id = sid
        iref.student_name = sname
        iref.identified = True
        iref.time = datetime.now()
        try:
            iref.save()
        except pw.IntegrityError:
            msg = "student id {} already entered elsewhere".format(censorID(sid))
            log.error("{} but {}".format(logbase, msg))
            return False, 409, msg
        tref.identified = True
        tref.save()
        log.info(
            'Paper {} ID\'d by "{}" as "{}" "{}"'.format(
                paper_num, user_name, censorID(sid), censorName(sname)
            )
        )
    return True, None, None
