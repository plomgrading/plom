from plom.db.tables import *

from datetime import datetime

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

import logging

log = logging.getLogger("DB")

from peewee import fn


# clean commands here.

## - upload functions
def uploadTestPage(
    self, test_number, page_number, version, original_name, file_name, md5, bundle_name
):
    # return value is either [True, <success message>] or
    # [False, stuff] - but need to distinguish between "discard this image" and "you should perhaps keep this image"
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", "Cannot find test {}".format(t)]
    pref = TPage.get_or_none(test=tref, page_number=page_number, version=version)
    if pref is None:
        return [
            False,
            "pageError",
            "Cannot find TPage,version {} for test {}".format(
                [page_number, versions], test_number
            ),
        ]
    if pref.scanned:
        # have already loaded an image for this page - so this is actually a duplicate
        log.debug("This appears to be a duplicate. Checking md5sums")
        if md5 == pref.image.md5sum:
            # Exact duplicate - md5sum of this image is sames as the one already in database
            return [
                False,
                "duplicate",
                "Exact duplicate of page already in database",
            ]
        # Deal with duplicate pages separately. return to sender (as it were)
        return [
            False,
            "collision",
            ["{}".format(pref.original_name), test_number, page_number, version],
        ]
    else:  # this is a new testpage. create an image and link it to the testpage
        # we need the bundle-ref now.
        bref = Bundle.get_or_none(name=bundle_name)
        if bref is None:
            return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

        with plomdb.atomic():
            pref.image = Image.create(
                original_name=original_name,
                file_name=file_name,
                md5sum=md5,
                bundle=bref,
            )
            pref.scanned = True
            pref.save()
            tref.used = True
            tref.save()
            # also link the image to an QPage, DNMPage, or IDPage
            # set the group as recently uploaded - use to trigger a "clean" later.
            gref = pref.group
            gref.recent_upload = True
            gref.save()
            if gref.group_type == "i":
                iref = gref.idgroups[0]
                idp = IDPage.create(idgroup=iref, image=pref.image, order=page_number)
            elif gref.group_type == "d":
                dref = gref.dnmgroups[0]
                dnmp = DNMPage.create(
                    dnmgroup=dref, image=pref.image, order=page_number
                )
            else:  # is a question page - always add to annotation 0.
                qref = gref.qgroups[0]
                aref = qref.annotations[0]
                ap = APage.create(annotation=aref, image=pref.image, order=page_number)

        log.info(
            "Uploaded image {} to tpv = {}.{}.{}".format(
                original_name, test_number, page_number, version
            )
        )
        return [
            True,
            "success",
            "Page saved as tpv = {}.{}.{}".format(test_number, page_number, version),
        ]


def replaceMissingTestPage(
    self, test_number, page_number, version, original_name, file_name, md5
):
    # we can actually just call uploadTPage - we just need to set the bundle_name.
    # hw is different because we need to verify no hw pages present already.
    rval = self.uploadTestPage(
        test_number,
        page_number,
        version,
        original_name,
        file_name,
        md5,
        "replacements",
    )
    if rval[0]:  # success - so trigger an update.
        tref = Test.get(test_number=test_number)
        self.updateTestAfterUpload(tref)
    return rval


def uploadHWPage(
    self, sid, question, order, original_name, file_name, md5, bundle_name
):
    # first of all find the test corresponding to that sid.
    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "SID does not correspond to any test on file."]
    tref = iref.test
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # should not happen.
        return [False, "Test/Question does not correspond to anything on file."]

    gref = qref.group
    href = HWPage.get_or_none(test=tref, group=gref, order=order)
    # the href should be none - but could exist if uploading HW in two bundles
    if href is not None:
        # we found a page with that order, so we need to put the uploaded page at the end.
        lastOrder = (
            HWPage.select(fn.MAX(HWPage.order))
            .where(HWPage.test == tref, HWPage.group == gref)
            .scalar()
        )
        order = lastOrder + 1
    # we need the bundle.
    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]
    # create a HW page
    with plomdb.atomic():
        aref = qref.annotations[0]
        # create image, hwpage, annotationpage and link.
        hw_image = Image.create(
            original_name=original_name, file_name=file_name, md5sum=md5, bundle=bref
        )
        href = HWPage.create(
            test=tref, group=gref, order=order, image=hw_image, version=qref.version
        )
        ap = APage.create(annotation=aref, image=hw_image, order=order)
        # set the recent_upload flag for the group and the used flag for the test
        gref.recent_upload = True
        gref.save()
        tref.used = True
        tref.save()
    return [True]


def replaceMissingHWQuestion(self, sid, question, original_name, file_name, md5):
    # this is basically same as uploadHWPage, excepting bundle+order are known.
    # and have to check if any HWPages present.
    # todo = merge this somehow with uploadHWPage? - most of function is sanity checks.

    order = 1
    bundle_name = "replacements"

    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "SID does not correspond to any test on file."]
    tref = iref.test
    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # should not happen.
        return [False, "Test/Question does not correspond to anything on file."]

    gref = qref.group
    href = HWPage.get_or_none(test=tref, group=gref)
    # the href should be none - but could exist if uploading HW in two bundles
    if href is not None:
        return [False, "HW pages already present."]

    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]
    # create a HW page
    with plomdb.atomic():
        aref = qref.annotations[0]
        # create image, hwpage, annotationpage and link.
        hw_image = Image.create(
            original_name=original_name, file_name=file_name, md5sum=md5, bundle=bref
        )
        href = HWPage.create(
            test=tref, group=gref, order=order, image=hw_image, version=qref.version
        )
        ap = APage.create(annotation=aref, image=hw_image, order=order)
        # set the recent_upload flag for the test
        tref.used = True
        tref.recent_upload = True
        tref.save()
    return [True]


def uploadUnknownPage(self, original_name, file_name, order, md5, bundle_name):
    iref = Image.get_or_none(md5sum=md5)
    if iref is not None:
        return [
            False,
            "duplicate",
            "Exact duplicate of page already in database",
        ]
    # make sure we know the bundle
    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]
    with plomdb.atomic():
        iref = Image.create(
            original_name=original_name, file_name=file_name, md5sum=md5, bundle=bref
        )
        uref = UnknownPage.create(image=iref, order=order)

    log.info("Uploaded image {} as unknown".format(original_name))
    return [True, "success", "Page saved in UnknownPage list"]


## clean up after uploads


def updateDNMGroup(self, dref):
    """Check all pages present in dnm group and set scanned flag accordingly.
    Since homework does not upload DNM pages, only check testpages.
    Will fail if some, but not all, pages scanned.
    Note - a DNM group can be empty.
    """
    gref = dref.group  # find the group-parent of the dnmgroup
    scan_list = []
    for p in gref.tpages:
        scan_list.append(p.scanned)
    if True in scan_list and False in scan_list:  # some scanned, but not all.
        return False
    # all test pages scanned (or all unscanned), so set things ready to go.
    with plomdb.atomic():
        gref.scanned = True
        gref.recent_upload = False
        gref.save()
        log.info("DNMGroup of test {} is all scanned.".format(gref.test.test_number))
    return True


def cleanIDGroup(self, iref):
    tref = iref.test
    with plomdb.atomic():
        iref.status = ""
        iref.user = None
        iref.time = datetime.now()
        iref.student_id = None
        iref.student_name = None
        iref.identified = False
        iref.time = datetime.now()
        iref.save()
        tref.identified = False
        tref.save()
        log.info("IDGroup of test {} cleaned.".format(tref.test_number))


def updateIDGroup(self, iref):
    """Update the ID task when new pages uploaded to IDGroup.
    If group is all scanned then the associated ID-task should be set to "todo".
    Note - be careful when group was auto-IDd (which happens when the associated user = HAL) - then we don't change anything.
    Note - this should only be triggered by a tpage upload.
    """

    # if IDGroup belongs to HAL then don't mess with it - was auto IDd.
    if iref.user == User.get(name="HAL"):
        auto_id = True
    else:
        auto_id = False
        # clean the ID-task and set test-identified flag to false.
        self.cleanIDGroup(iref)

    # grab associated parent group
    gref = iref.group
    # now check if all test-pages pesent - note none-present when a hw upload.
    for p in gref.tpages:
        if p.scanned is False:
            return False  # not yet completely present.

    # all test ID pages present, and group cleaned, so set things ready to go.
    with plomdb.atomic():
        gref.scanned = True
        gref.recent_upload = False
        gref.save()
        if auto_id is False:
            iref.status = "todo"
            iref.save()
            log.info(
                "IDGroup of test {} is ready to be identified.".format(
                    gref.test.test_number
                )
            )
        else:
            log.info(
                "IDGroup of test {} is present and already IDd.".format(
                    gref.test.test_number
                )
            )
    return True


def cleanQGroup(self, qref):
    tref = qref.test
    with plomdb.atomic():
        # update 0th annotation but move other annotations to oldannotations
        # set starting edition for oldannot to either 0 or whatever was last.
        if qref.oldannotations.count() == 0:
            ed = 0
        else:
            ed = qref.oldannotations[-1].edition

        for aref in qref.annotations:
            if aref.edition == 0:  # update 0th edition.
                # delete old apages
                for p in aref.apages:
                    p.delete_instance()
                # now create new ones - tpages, then hwpage, then expages, finally any lpages
                ord = 0
                for p in qref.group.tpages.order_by(TPage.page_number):
                    if p.scanned:  # make sure the tpage is actually scanned.
                        ord += 1
                        print("Trying to add tpage {}".format(p))
                        APage.create(annotation=aref, image=p.image, order=ord)
                for p in qref.group.hwpages.order_by(HWPage.order):
                    ord += 1
                    print("Trying to add hwpage {}".format(p))
                    APage.create(annotation=aref, image=p.image, order=ord)
                for p in qref.group.expages.order_by(EXPage.order):
                    ord += 1
                    print("Trying to add expage {}".format(p))
                    APage.create(annotation=aref, image=p.image, order=ord)
                for p in tref.lpages.order_by(LPage.order):
                    ord += 1
                    print("Trying to add lpage {}".format(p))
                    APage.create(annotation=aref, image=p.image, order=ord)
            else:
                ed += 1
                # make new oldannot using data from aref
                oaref = OldAnnotation.create(
                    qgroup=aref.qgroup,
                    user=aref.user,
                    image=aref.image,
                    edition=ed,
                    plom_file=aref.plom_file,
                    comment_file=aref.comment_file,
                    mark=aref.mark,
                    marking_time=aref.marking_time,
                    time=aref.time,
                    tags=aref.tags,
                )
                # make oapges
                for pref in aref.apages:
                    OAPage.create(
                        old_annotation=oaref, order=pref.order, image=pref.image
                    )
                # now delete the apages and then the annotation-image and finally the annotation.
                for pref in aref.apages:
                    pref.delete_instance()
                # delete the annotated image from table.
                aref.image.delete_instance()
                # finally delete the annotation itself.
                aref.delete_instance()

        qref.user = None
        qref.status = ""
        qref.marked = False
        qref.save()
        tref.marked = False
        tref.save()

    log.info("QGroup {} of test {} cleaned".format(qref.question, tref.test_number))


def updateQGroup(self, qref):
    # TODO = if loose / extra pages present in test, then test is not ready.

    # clean up the QGroup and its annotations
    self.cleanQGroup(qref)
    # note - the sumdata will be updated elsewhere.

    gref = qref.group

    # when some but not all TPages present - not ready
    # when 0 pages present - not ready
    # otherwise ready.
    scan_list = [p.scanned for p in gref.tpages]  # list never zero length.
    if True in scan_list:  # some tpages scanned.
        if False in scan_list:  # some tpages unscanned - definitely not ready to go.
            log.info("Group {} is only half-scanned - not ready".format(gref.gid))
            return False
        else:
            pass  # all tpages scanned - so ready to go.
    else:  # all tpages unscanned - check hw pages
        if gref.hwpages.count() == 0:  # no  hw pages present - not ready
            log.info(
                "Group {} has no scanned tpages and no hwpages - not ready".format(
                    gref.gid
                )
            )
            return False
        else:
            pass  # no unscanned tpages, but not hw pages - so ready to go.

    # If we get here - we are ready to go.
    with plomdb.atomic():
        gref.scanned = True
        gref.recent_upload = False
        qref.status = "todo"
        qref.save()
        gref.save()
        log.info(
            "QGroup {} of test {} is ready to be marked.".format(
                qref.question, qref.test.test_number
            )
        )
    return True


def cleanSDataNotReady(self, tref):
    sref = tref.sumdata[0]
    with plomdb.atomic():
        sref.sum_mark = None
        sref.user = None
        sref.time = datetime.now()
        sref.status = ""
        sref.save()
        tref.totalled = False
        tref.save()
        log.info(
            "SumData of test {} cleaned but not yet ready for totalling.".format(
                tref.test_number
            )
        )


def updateGroupAfterUpload(self, gref):
    """Check the type of the group and update accordingly.
    return success/failure of that update.
    """
    if gref.group_type == "i":
        return self.updateIDGroup(gref.idgroups[0])
    elif gref.group_type == "d":
        return self.updateDNMGroup(gref.dnmgroups[0])
    elif gref.group_type == "q":
        # if the group is ready - all good.
        if self.updateQGroup(gref.qgroups[0]):
            return True
        else:
            # since qgroup not ready, we cannnot total yet.
            self.cleanSDataNotReady(gref.test)
            return False
    else:
        raise ValueError("Tertium non datur: should never happen")


def cleanAndReadySData(self, tref):
    sref = tref.sumdata[0]
    with plomdb.atomic():
        sref.sum_mark = None
        sref.user = None
        sref.time = datetime.now()
        tref.totalled = False
        sref.status = "todo"
        sref.save()
        tref.save()
        log.info(
            "SumData of test {} cleaned and ready for totalling.".format(
                tref.test_number
            )
        )


def checkTestScanned(self, tref):
    """Check if all groups scanned."""
    for gref in tref.groups:
        if gref.group_type == "q":
            if gref.scanned is False:
                log.info(
                    "Group {} of test {} is not scanned - test not ready.".format(
                        gref.gid, tref.test_number
                    )
                )
                return False
        elif gref.group_type == "d":
            log.info(
                "DNM Group {} of test {} is not scanned - ignored.".format(
                    gref.gid, tref.test_number
                )
            )
        elif gref.group_type == "i":
            if gref.idgroups[0].identified:
                log.info(
                    "ID Group {} of test {} is identified".format(
                        gref.gid, tref.test_number
                    )
                )
            elif not gref.scanned:
                log.info(
                    "ID Group {} of test {} is not scanned - test not ready.".format(
                        gref.gid, tref.test_number
                    )
                )

    return True


def updateTestAfterUpload(self, tref):
    update_count = 0
    # check each group in the test
    for gref in tref.groups:
        if self.updateGroupAfterUpload(gref):
            update_count += 1

    # now make sure the whole thing is scanned and update the sumdata if ready to go.
    if self.checkTestScanned(tref):
        # set the sdata ready to go
        self.cleanAndReadySData(tref)
        # set the test as scanned
        with plomdb.atomic():
            tref.scanned = True
            log.info("Test {} is scanned".format(tref.test_number))
            tref.save()

    return update_count


def processUpdatedTests(self):
    """Update the groups of tests in response to new uploads.
    The recent_upload flag is set either for the whole test or for a given group.
    If the whole test then we must update every group - this happens when lpages are uploaded.
    If a group is flagged, then we update just that group - this happens when tpages or hwpages are uploaded.
    """
    update_count = 0  # how many groups updated
    # process whole tests first
    for tref in Test.select().where(Test.recent_upload == True):
        update_count += self.updateTestAfterUpload(tref)

    # make a dict of tests that need checking for ready-status
    tests_to_update = {}
    # then process groups
    for gref in Group.select().where(Group.recent_upload == True):
        if self.updateGroupAfterUpload(gref):
            update_count += 1
            tests_to_update[gref.test] = 1
    for tref in tests_to_update:
        if self.checkTestScanned(tref):
            # set the sdata ready to go
            self.cleanAndReadySData(tref)
            # set the test as scanned
            with plomdb.atomic():
                tref.scanned = True
                log.info("Test {} is scanned".format(tref.test_number))
                tref.save()

    return [True, update_count]


# still todo below


def fileOfScannedPage(self, t, p, v):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        return None
    pref = Page.get_or_none(test=tref, page_number=p, version=v)
    if pref is None:
        return None
    return pref.file_name


def createDiscardedPage(self, oname, fname, md5, r, tpv):
    DiscardedPage.create(
        original_name=oname, file_name=fname, md5sum=md5, reason=r, tpv=tpv
    )


def removeScannedPage(self, fname, nname):
    pref = Page.get_or_none(file_name=fname)
    if pref is None:
        return False
    with plomdb.atomic():
        DiscardedPage.create(
            file_name=nname, original_name=pref.original_name, md5sum=pref.md5sum
        )
        pref.scanned = False
        pref.original_name = None
        pref.file_name = None
        pref.md5sum = None
        pref.scanned = False
        pref.save()
    log.info("Removing scanned page with fname = {}".format(fname))

    tref = pref.test
    gref = pref.group
    # now update the group
    if gref.group_type == "d":
        rlist = self.invalidateDNMGroup(tref, gref)
    elif gref.group_type == "i":
        rlist = self.invalidateIDGroup(tref, gref)
    elif gref.group_type == "m":
        rlist = self.invalidateQGroup(tref, gref)
    return [True, rlist]


def invalidateDNMGroup(self, gref):
    with plomdb.atomic():
        tref.scanned = False
        tref.save()
        gref.scanned = False
        gref.save()
    log.info("Invalidated dnm {}".format(gref.gid))
    return []


def invalidateIDGroup(self, tref, gref):
    iref = gref.idgroups[0]
    with plomdb.atomic():
        tref.scanned = False
        tref.identified = False
        tref.save()
        gref.scanned = False
        gref.save()
        iref.status = ""
        iref.user = None
        iref.time = datetime.now()
        iref.student_id = None
        iref.student_name = None
        iref.save()
    log.info("Invalidated IDGroup {}".format(gref.gid))
    return []


def invalidateQGroup(self, tref, gref, delPage=True):
    # When we delete a page, set "scanned" to false for group+test
    # If we are adding a page then we don't have to do that.
    qref = gref.qgroups[0]
    sref = tref.sumdata[0]
    rval = []
    with plomdb.atomic():
        # update the test
        if delPage:
            tref.scanned = False
        tref.marked = False
        tref.totalled = False
        tref.save()
        # update the group
        if delPage:
            gref.scanned = False
            gref.save()
        # update the sumdata
        sref.status = ""
        sref.sum_mark = None
        sref.user = None
        sref.time = datetime.now()
        sref.summed = False
        sref.save()
        # update the qgroups - first get file_names if they exist
        if qref.marked:
            rval = [
                qref.annotatedFile,
                qref.plom_file,
                qref.comment_file,
            ]
        qref.marked = False
        qref.status = ""
        qref.annotatedFile = None
        qref.plom_file = None
        qref.comment_file = None
        qref.mark = None
        qref.markingTime = None
        qref.tags = ""
        qref.user = None
        qref.time = datetime.now()
        qref.save
    log.info("Invalidated question {}".format(gref.gid))
    return rval


def uploadLPage(self, sid, order, oname, nname, md5):
    # first of all find the test corresponding to that sid.
    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "SID does not correspond to any test on file."]
    tref = iref.test
    xref = LPage.get_or_none(test=tref, order=order)  # this should be none.
    if xref is not None:
        # we found a page with that order, so we need to put the uploaded page at the end.
        lastOrder = LPage.select(fn.MAX(LPage.order)).where(LPage.test == tref).scalar()
        if lastOrder is None:
            order = 1
        else:
            order = lastOrder + 1
    # create one.
    with plomdb.atomic():
        # create image, LPage, and link.
        img = Image.create(original_name=oname, file_name=nname, md5sum=md5)
        xref = LPage.create(test=tref, order=order, image=img)
        # now we have to append this page to every annotation.
        # BIG TODO - improve this so human decides what goes where.
        for qref in QGroup.select().where(QGroup.test == tref):
            aref = qref.annotations[0]
            lastOrder = (
                APage.select(fn.MAX(APage.order))
                .where(APage.annotation == aref)
                .scalar()
            )
            if lastOrder is None:
                order = 0
            else:
                order = lastOrder + 1
            ap = APage.create(annotation=aref, image=img, order=order)
        # set the recent_upload flag for the test
        tref.used = True
        tref.recent_upload = True
        tref.save()
    return [True]


def processUpdatedQGroup(self, tref, qref):
    # clean up the QGroup and its annotations
    self.cleanQGroup(tref, qref)
    # now some logic.
    # if homework pages present - ready to go.
    # elif all testpages present - ready to go.
    # else - not ready.
    # BUT if there are LPages then we are ready to go.

    gref = qref.group

    if tref.lpages.count() == 0:
        # check if HW pages = 0
        if qref.group.hwpages.count() == 0:
            # then check for testpages
            for p in gref.tpages:  # there is always at least one.
                if p.scanned is False:  # missing a test-page - not ready.
                    return False

    # otherwise we are ready to go.
    with plomdb.atomic():
        gref.scanned = True
        qref.status = "todo"
        qref.save()
        gref.save()
        log.info(
            "QGroup {} of test {} is ready to be marked.".format(
                qref.question, tref.test_number
            )
        )
    return True


def processSpecificUpdatedTest(self, tref):
    log.info("Updating test {}.".format(tref.test_number))
    rval = []
    rval.append(self.processUpdatedIDGroup(tref, tref.idgroups[0]))
    rval.append(self.processUpdatedDNMGroup(tref, tref.dnmgroups[0]))
    for qref in tref.qgroups:
        rval.append(self.processUpdatedQGroup(tref, qref))
    # clean out the sumdata and set ready status.
    self.cleanSData(tref, tref.sumdata[0])
    self.processUpdatedSData(tref, tref.sumdata[0])
    # now clear the update flag.
    with plomdb.atomic():
        tref.recent_upload = False
        if all(rv for rv in rval):
            log.info("Test {} ready to go.".format(tref.test_number))
            tref.scanned = True
        else:
            log.info("Test {} still missing pages - {}.".format(tref.test_number, rval))
        tref.save()


def uploadCollidingPage(self, t, p, v, oname, nname, md5):
    tref = Test.get_or_none(test_number=t)
    if tref is None:
        return [False, "testError", "Cannot find test {}".format(t)]
    pref = TPage.get_or_none(test=tref, page_number=p, version=v)
    if pref is None:
        return [
            False,
            "pageError",
            "Cannot find page,version {} for test {}".format([p, v], t),
        ]
    if not pref.scanned:
        return [
            False,
            "original",
            "This is not a collision - this page was not scanned previously",
        ]
    # check this against other collisions
    for cp in pref.collisions:
        if md5 == cp.md5sum:
            # Exact duplicate - md5sum of this image is sames as the one already in database
            return [
                False,
                "duplicate",
                "Exact duplicate of page already in database",
            ]
    with plomdb.atomic():
        cref = CollidingPage.create(
            original_name=oname, file_name=nname, md5sum=md5, page=pref
        )
        cref.save()
    log.info("Uploaded image {} as collision of tpv={}.{}.{}".format(oname, t, p, v))
    return [
        True,
        "success",
        "Colliding page saved, attached to {}.{}.{}".format(t, p, v),
    ]
