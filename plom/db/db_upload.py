from plom.db.tables import *

from datetime import datetime
import uuid

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName

import logging

log = logging.getLogger("DB")

from peewee import fn


class PlomBundleImageDuplicationException(Exception):
    """An exception triggered when trying to upload the same image from the same bundle twice."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


## - create an image and return the reference
def createNewImage(self, original_name, file_name, md5, bundle_ref, bundle_order):
    # todo = this should check for existence of (bundle_ref, bundle_order) before building.
    # if exists then send fail message.
    if Image.get_or_none(bundle=bundle_ref, bundle_order=bundle_order):
        raise PlomBundleImageDuplicationException(
            "Image number {} from bundle {} uploaded previously.".format(
                bundle_order, bundle_ref.name
            )
        )
    else:
        return Image.create(
            original_name=original_name,
            file_name=file_name,
            md5sum=md5,
            bundle=bundle_ref,
            bundle_order=bundle_order,
        )


## - upload functions


def attachImageToTPage(self, test_ref, page_ref, image_ref):
    # can be called by an upload, but also by move-misc-to-tpage
    with plomdb.atomic():
        page_ref.image = image_ref
        page_ref.scanned = True
        page_ref.save()
        test_ref.used = True
        test_ref.save()
        # also link the image to an QPage, DNMPage, or IDPage
        # set the group as recently uploaded - use to trigger a "clean" later.
        gref = page_ref.group
        gref.recent_upload = True
        gref.save()
        if gref.group_type == "i":
            iref = gref.idgroups[0]
            idp = IDPage.create(
                idgroup=iref, image=image_ref, order=page_ref.page_number
            )
        elif gref.group_type == "d":
            dref = gref.dnmgroups[0]
            dnmp = DNMPage.create(
                dnmgroup=dref, image=image_ref, order=page_ref.page_number
            )
        else:  # is a question page - always add to annotation 0.
            qref = gref.qgroups[0]
            aref = qref.annotations[0]
            ap = APage.create(
                annotation=aref, image=image_ref, order=page_ref.page_number
            )


def uploadTestPage(
    self,
    test_number,
    page_number,
    version,
    original_name,
    file_name,
    md5,
    bundle_name,
    bundle_order,
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
            ["{}".format(pref.image.original_name), test_number, page_number, version],
        ]
    else:  # this is a new testpage. create an image and link it to the testpage
        # we need the bundle-ref now.
        bref = Bundle.get_or_none(name=bundle_name)
        if bref is None:
            return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

        try:
            image_ref = self.createNewImage(
                original_name, file_name, md5, bref, bundle_order
            )
        except PlomBundleImageDuplicationException:
            return [
                False,
                "bundle image duplication error",
                "Image number {} from bundle {} uploaded previously".format(
                    bundle_order,
                    bundle_name,
                ),
            ]

        self.attachImageToTPage(tref, pref, image_ref)

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
    # make sure owners of tasks in that test not logged in
    tref = Test.get_or_none(Test.test_number == test_number)
    if tref is None:
        return [False, "Cannot find that test"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    # we can actually just call uploadTPage - we just need to set the bundle_name and bundle_order.
    # hw is different because we need to verify no hw pages present already.

    bref = Bundle.get_or_none(name="replacements")
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

    # find max bundle_order within that bundle
    bundle_order = 0
    for iref in bref.images:
        bundle_order = max(bundle_order, iref.bundle_order)
    bundle_order += 1

    #
    rval = self.uploadTestPage(
        test_number,
        page_number,
        version,
        original_name,
        file_name,
        md5,
        "replacements",
        bundle_order,
    )
    if rval[0]:  # success - so trigger an update.
        tref = Test.get(test_number=test_number)
        self.updateTestAfterUpload(tref)
    return rval


def createNewHWPage(self, test_ref, qdata_ref, order, image_ref):
    # can be called by an upload, but also by move-misc-to-tpage
    # create a HW page
    gref = qdata_ref.group
    with plomdb.atomic():
        aref = qdata_ref.annotations[0]
        # create image, hwpage, annotationpage and link.
        href = HWPage.create(
            test=test_ref,
            group=gref,
            order=order,
            image=image_ref,
            version=qdata_ref.version,
        )
        ap = APage.create(annotation=aref, image=image_ref, order=order)
        # set the recent_upload flag for the group and the used flag for the test
        gref.recent_upload = True
        gref.save()
        test_ref.used = True
        test_ref.save()


def uploadHWPage(
    self,
    sid,
    questions,
    order,
    original_name,
    file_name,
    md5,
    bundle_name,
    bundle_order,
):
    # first of all find the test corresponding to that sid.
    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "SID does not correspond to any test on file."]
    tref = iref.test

    # we need the bundle.
    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

    try:
        image_ref = self.createNewImage(
            original_name, file_name, md5, bref, bundle_order
        )
    except PlomBundleImageDuplicationException:
        return [
            False,
            "bundle image duplication error",
            "Image number {} from bundle {} uploaded previously".format(
                bundle_order,
                bundle_name,
            ),
        ]

    if not isinstance(questions, list):
        questions = [questions]
    if len(questions) >= 1:
        log.info(
            'upload: tef={} going to loop over questions="{}"'.format(tref, questions)
        )
    qref_list = []
    for question in questions:
        qref = QGroup.get_or_none(test=tref, question=question)
        if qref is None:  # should not happen.
            return [False, "Test/Question does not correspond to anything on file."]
        qref_list.append(qref)

    for question, qref in zip(questions, qref_list):
        gref = qref.group
        href = HWPage.get_or_none(test=tref, group=gref, order=order)
        if href is not None:
            # we found a page with that order, so we need to put the uploaded page at the end.
            lastOrder = (
                HWPage.select(fn.MAX(HWPage.order))
                .where(HWPage.test == tref, HWPage.group == gref)
                .scalar()
            )
            log.info(
                "hwpage order collision: question={}, order={}; changing to lastOrder+1={})".format(
                    question, order, lastOrder + 1
                )
            )
            tmp_order = lastOrder + 1
        else:
            # no page at that order so ok to insert using user-specified order.
            tmp_order = order

        log.info(
            "creating new hwpage tref={}, question={}, order={}".format(
                tref, question, tmp_order
            )
        )
        self.createNewHWPage(tref, qref, tmp_order, image_ref)
    return [True]


def createNewLPage(self, test_ref, order, image_ref):
    # can be called by an upload, but also by move-misc-to-tpage
    # create an Lpage
    with plomdb.atomic():
        lref = LPage.create(
            test=test_ref,
            order=order,
            image=image_ref,
        )
        # this needs to be appended to each qgroup
        for qref in test_ref.qgroups:
            gref = qref.group
            aref = qref.annotations[0]
            # create annotationpage and link.
            ap = APage.create(annotation=aref, image=image_ref, order=order)
            # set the recent_upload flag for the group and the used flag for the test
            gref.recent_upload = True
            gref.save()
        test_ref.used = True
        test_ref.save()


def uploadLPage(
    self, sid, order, original_name, file_name, md5, bundle_name, bundle_order
):
    # first of all find the test corresponding to that sid.
    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "SID does not correspond to any test on file."]
    tref = iref.test

    lref = LPage.get_or_none(test=tref, order=order)
    # the lref should be none - but could exist if uploading loose pages in two bundles
    if lref is not None:
        # we found a page with that order, so we need to put the uploaded page at the end.
        lastOrder = LPage.select(fn.MAX(LPage.order)).where(LPage.test == tref).scalar()
        order = lastOrder + 1
    # we need the bundle.
    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

    try:
        image_ref = self.createNewImage(
            original_name, file_name, md5, bref, bundle_order
        )
    except PlomBundleImageDuplicationException:
        return [
            False,
            "bundle image duplication error",
            "Image number {} from bundle {} uploaded previously".format(
                bundle_order,
                bundle_name,
            ),
        ]

    self.createNewLPage(tref, order, image_ref)
    return [True]


def getSIDFromTest(self, test_number):
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "Cannot find test"]
    iref = tref.idgroups[0]
    if iref.identified:
        return [True, iref.student_id]
    else:
        return [False, "Test not yet identified"]


def sidToTest(self, student_id):
    iref = IDGroup.get_or_none(student_id=student_id)
    if iref is None:
        return [False, "Cannot find test with sid {}".format(student_id)]
    else:
        return [True, iref.test.test_number]


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
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    qref = QGroup.get_or_none(test=tref, question=question)
    if qref is None:  # should not happen.
        return [False, "Test/Question does not correspond to anything on file."]

    gref = qref.group
    href = HWPage.get_or_none(test=tref, group=gref)
    # the href should be none - but could exist if uploading HW in two bundles
    if href is not None:
        return [False, "present", "HW pages already present."]

    bref = Bundle.get_or_none(name=bundle_name)
    if bref is None:
        return [False, "bundleError", "Cannot find bundle {}".format(bundle_name)]

    # find max bundle_order within that bundle
    bundle_order = 0
    for iref in bref.images:
        bundle_order = max(bundle_order, iref.bundle_order)
    bundle_order += 1

    # create an image for the image-file

    try:
        image_ref = self.createNewImage(
            original_name, file_name, md5, bref, bundle_order
        )
    except PlomBundleImageDuplicationException:
        return [
            False,
            "bundle image duplication error",
            "Image number {} from bundle {} uploaded previously".format(
                bundle_order,
                bundle_name,
            ),
        ]

    # create the associated HW page
    self.createNewHWPage(tref, qref, order, image_ref)
    # and do an update.
    self.updateTestAfterUpload(tref)

    return [True]


def uploadUnknownPage(
    self, original_name, file_name, order, md5, bundle_name, bundle_order
):
    # TODO - remove 'order' here - it is superceded by 'bundle_order'

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

        try:
            iref = Image.create(
                original_name=original_name,
                file_name=file_name,
                md5sum=md5,
                bundle=bref,
                bundle_order=bundle_order,
            )
        except PlomBundleImageDuplicationException:
            return [
                False,
                "bundle image duplication error",
                "Image number {} from bundle {} uploaded previously".format(
                    bundle_order,
                    bundle_name,
                ),
            ]
        uref = UnknownPage.create(image=iref, order=order)

    log.info("Uploaded image {} as unknown".format(original_name))
    return [True, "success", "Page saved in UnknownPage list"]


def uploadCollidingPage(
    self,
    test_number,
    page_number,
    version,
    original_name,
    file_name,
    md5,
    bundle_name,
    bundle_order,
):
    """Upload given file as a collision of tpage given by tpv.

    Check test and tpage exist - fail if they don't.
    Check against other collisions of that tpage - fail if already exists.
    Create image (careful check against bundle)
    Create collision linked to the tpage.
    """

    # simple sanity tests against test and tpages
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", "Cannot find test {}".format(t)]
    pref = TPage.get_or_none(test=tref, page_number=page_number, version=version)
    if pref is None:
        return [
            False,
            "pageError",
            "Cannot find page,version {} for test {}".format(
                [page_number, version], test_number
            ),
        ]
    if not pref.scanned:
        return [
            False,
            "original",
            "This is not a collision - this page was not scanned previously",
        ]
    # check this against other collisions for that page
    for cp in pref.collisions:
        if md5 == cp.image.md5sum:
            # Exact duplicate - md5sum of this image is sames as the one already in database
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
        try:
            iref = Image.create(
                original_name=original_name,
                file_name=file_name,
                md5sum=md5,
                bundle=bref,
                bundle_order=bundle_order,
            )
        except PlomBundleImageDuplicationException:
            return [
                False,
                "bundle image duplication error",
                "Image number {} from bundle {} uploaded previously".format(
                    bundle_order,
                    bundle_name,
                ),
            ]
        cref = CollidingPage.create(tpage=pref, image=iref)
        cref.save()
    log.info(
        "Uploaded image {} as collision of tpv={}.{}.{}".format(
            original_name, test_number, page_number, version
        )
    )
    return [
        True,
        "success",
        "Colliding page saved, attached to {}.{}.{}".format(
            test_number, page_number, version
        ),
    ]


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
                # set the integrity_check string to a UUID
                ord = 0
                integrity_check = uuid.uuid4().hex
                for p in qref.group.tpages.order_by(TPage.page_number):
                    if p.scanned:  # make sure the tpage is actually scanned.
                        ord += 1
                        APage.create(annotation=aref, image=p.image, order=ord)
                for p in qref.group.hwpages.order_by(HWPage.order):
                    ord += 1
                    APage.create(annotation=aref, image=p.image, order=ord)
                for p in qref.group.expages.order_by(EXPage.order):
                    ord += 1
                    APage.create(annotation=aref, image=p.image, order=ord)
                for p in tref.lpages.order_by(LPage.order):
                    ord += 1
                    APage.create(annotation=aref, image=p.image, order=ord)
                aref.integrity_check = integrity_check
                aref.save()
            else:
                ed += 1
                # make new oldannot using data from aref
                oaref = OldAnnotation.create(
                    qgroup=aref.qgroup,
                    user=aref.user,
                    aimage=aref.aimage,
                    edition=ed,
                    plom_file=aref.plom_file,
                    comment_file=aref.comment_file,
                    mark=aref.mark,
                    marking_time=aref.marking_time,
                    time=aref.time,
                    tags=aref.tags,
                    integrity_check=aref.integrity_check,
                )
                # make oapges
                for pref in aref.apages:
                    OAPage.create(
                        old_annotation=oaref, order=pref.order, image=pref.image
                    )
                # now delete the apages and then the annotation-image and finally the annotation.
                for pref in aref.apages:
                    pref.delete_instance()
                # delete the annotated image from table (if it exists).
                if aref.aimage is not None:
                    aref.aimage.delete_instance()
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
        return self.updateQGroup(gref.qgroups[0])
    else:
        raise ValueError("Tertium non datur: should never happen")


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
            if gref.scanned is False:
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
                return False

    return True


def updateTestAfterUpload(self, tref):
    update_count = 0
    # check each group in the test
    for gref in tref.groups:
        if self.updateGroupAfterUpload(gref):
            update_count += 1

    # now make sure the whole thing is scanned.
    if self.checkTestScanned(tref):
        # set the test as scanned
        with plomdb.atomic():
            tref.scanned = True
            log.info("Test {} is scanned".format(tref.test_number))
            tref.save()

    return update_count


def processUpdatedTests(self):
    """Update the groups of tests in response to new uploads.

    Returns:
        int: how many groups updated.

    The recent_upload flag is set either for the whole test or for a given group.
    If the whole test then we must update every group - this happens when lpages are uploaded.
    If a group is flagged, then we update just that group - this happens when tpages or hwpages are uploaded.

    """
    update_count = 0
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
            # set the test as scanned
            with plomdb.atomic():
                tref.scanned = True
                log.info("Test {} is scanned".format(tref.test_number))
                tref.save()

    return update_count


def removeAllScannedPages(self, test_number):
    # return the give test to the pre-upload state.
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", "Cannot find test {}".format(t)]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    with plomdb.atomic():
        # move all tpages to discards
        for pref in tref.tpages:
            if pref.scanned:  # move the tpage to a discard
                iref = pref.image
                DiscardedPage.create(
                    image=iref,
                    reason="Discarded scan of t{}.{}".format(
                        test_number, pref.page_number
                    ),
                )
                pref.image = None
                pref.scanned = False
                pref.save()
        # remove all hwpages
        for pref in tref.hwpages:
            iref = pref.image
            DiscardedPage.create(
                image=iref,
                reason="Discarded scan of h.{}.{}.{}".format(
                    test_number, pref.group.qgroups[0].question, pref.order
                ),
            )
            pref.delete_instance()
        # remove all expages
        for pref in tref.expages:
            iref = pref.image
            DiscardedPage.create(
                image=iref,
                reason="Discarded scan of ex{}.{}.{}".format(
                    test_number, pref.group.qgroups[0].question, pref.order
                ),
            )
            pref.delete_instance()
        # remove all lpages
        for pref in tref.lpages:
            iref = pref.image
            DiscardedPage.create(
                image=iref,
                reason="Discarded scan of l.{}.{}".format(
                    test_number,
                    pref.order,
                ),
            )
            pref.delete_instance()
        # set all the groups as unscanned
        for gref in tref.groups:
            gref.scanned = False
            gref.save()
        # finally - set this flag to trigger an update.
        tref.recent_upload = True
        tref.scanned = False
        tref.used = False
        tref.save()
    self.updateTestAfterUpload(tref)
    return [True, "Test {} wiped clean".format(test_number)]
