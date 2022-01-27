# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from datetime import datetime
import logging
import uuid

from peewee import fn

from plom.db.tables import plomdb
from plom.db.tables import Bundle, IDGroup, Image, QGroup, Test, User
from plom.db.tables import Annotation, APage, DNMPage, EXPage, HWPage, IDPage, TPage
from plom.db.tables import CollidingPage, DiscardedPage, UnknownPage


log = logging.getLogger("DB")


class PlomBundleImageDuplicationException(Exception):
    """An exception triggered when trying to upload the same image from the same bundle twice."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


# - create an image and return the reference
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


# - upload functions


def attachImageToTPage(self, test_ref, page_ref, image_ref):
    # can be called by an upload, but also by move-misc-to-tpage
    with plomdb.atomic():
        page_ref.image = image_ref
        page_ref.scanned = True
        page_ref.save()
        test_ref.used = True
        test_ref.save()


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
        return [False, "testError", f"Cannot find test {test_number}"]
    pref = TPage.get_or_none(test=tref, page_number=page_number, version=version)
    if pref is None:
        return [
            False,
            "pageError",
            f"Cannot find TPage {page_number} ver{version} for test {test_number}",
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
            return [False, "bundleError", f'Cannot find bundle "{bundle_name}"']

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

        # find all qgroups with non-outdated annotations using that image
        groups_to_update = self.get_groups_using_image(pref.image)
        # add the group that should use that page
        groups_to_update.add(pref.group)
        # update the test.
        self.updateTestAfterChange(tref, group_refs=groups_to_update)
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

    bref = Bundle.get_or_none(name="__replacements__system__")
    if bref is None:
        return [False, "bundleError", 'Cannot find bundle "replacements"']

    # find max bundle_order within that bundle
    bundle_order = 0
    for iref in bref.images:
        bundle_order = max(bundle_order, iref.bundle_order)
    bundle_order += 1

    # we now 'upload' our replacement page using self.uploadTestPage
    # this also triggers an update on the test, so we don't have to
    # call self.updateTestAfterChange explicitly.
    rval = self.uploadTestPage(
        test_number,
        page_number,
        version,
        original_name,
        file_name,
        md5,
        "__replacements__system__",
        bundle_order,
    )
    return rval


def createNewHWPage(self, test_ref, qdata_ref, order, image_ref):
    # can be called by an upload, but also by move-misc-to-tpage
    # create a HW page and return a ref to it
    gref = qdata_ref.group
    with plomdb.atomic():
        # get the first non-outdated annotation for the group
        aref = (
            gref.qgroups[0]
            .annotations.where(Annotation.outdated == False)  # noqa: E712
            .order_by(Annotation.edition)
            .get()
        )
        # create image, hwpage, annotationpage and link.
        pref = HWPage.create(
            test=test_ref,
            group=gref,
            order=order,
            image=image_ref,
            version=qdata_ref.version,
        )
        APage.create(annotation=aref, image=image_ref, order=order)
        test_ref.used = True
        test_ref.save()
        return pref


def doesHWHaveIDPage(self, sid):
    iref = IDGroup.get_or_none(student_id=sid)
    if iref is None:
        return [False, "unknown"]
    # we know that SID, get the test and student name.
    tref = iref.test
    if len(iref.idpages) > 0:
        return [True, "idpage", tref.test_number, iref.student_name]
    else:
        return [False, "noid", tref.test_number, iref.student_name]


def getMissingDNMPages(self, test_number):
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "unknown"]
    dref = tref.dnmgroups[0]
    gref = dref.group
    unscanned_list = []
    for pref in gref.tpages:
        if not pref.scanned:
            unscanned_list.append(pref.page_number)
    return [True, unscanned_list]


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
        return [False, "bundleError", f'Cannot find bundle "{bundle_name}"']

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
        pref = self.createNewHWPage(tref, qref, tmp_order, image_ref)
        # get all groups that use that image
        groups_to_update = self.get_groups_using_image(image_ref)
        groups_to_update.add(pref.group)
        self.updateTestAfterChange(tref, group_refs=groups_to_update)
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
    bundle_name = "__replacements__system__"

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
        return [False, "bundleError", f'Cannot find bundle "{bundle_name}"']

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
    pref = self.createNewHWPage(tref, qref, order, image_ref)
    # find groups using that image
    groups_to_update = self.get_groups_using_image(image_ref)
    # add in the group that must use it
    groups_to_update.add(pref.group)
    # and do an update
    self.updateTestAfterChange(tref, group_refs=groups_to_update)

    return [True]


def uploadUnknownPage(
    self, original_name, file_name, order, md5, bundle_name, bundle_order
):
    # TODO - remove 'order' here - it is superseded by 'bundle_order'

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
        return [False, "bundleError", f'Cannot find bundle "{bundle_name}"']
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
        UnknownPage.create(image=iref, order=order)

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
        return [False, "testError", f"Cannot find test {test_number}"]
    pref = TPage.get_or_none(test=tref, page_number=page_number, version=version)
    if pref is None:
        return [
            False,
            "pageError",
            f"Cannot find page {page_number} ver{version} for test {test_number}",
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
        return [False, "bundleError", f'Cannot find bundle "{bundle_name}"']
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


# update groups and test after changes


def updateDNMGroup(self, dref):
    """Recreate the DNM pages of dnm-group, and check if all present.
    Set scanned flag accordingly.
    Since homework does not upload DNM pages, only check testpages.
    Will fail if there is an unscanned tpage.
    Note - a DNM group can be empty - then will succeed.
    Also note - hwscan upload creates and uploads tpages for DNM groups if needed.

    args:
        dref (DNMGroup): a reference to the DNM group to be updated

    returns:
        bool: True means DNM group is ready (ie all tpages scanned),
              False otherwise (ie missing some tpages)
    """
    # get the parent-group of the dnm-group
    gref = dref.group
    # first remove any old dnmpages
    for pref in dref.dnmpages:
        pref.delete_instance()
    # now rebuild them, keeping track of which are scanned or not
    # only have to check tpages - not hw or extra pages.
    scan_list = []
    for pref in gref.tpages:
        scan_list.append(pref.scanned)
        if pref.scanned:
            DNMPage.create(dnmgroup=dref, image=pref.image, order=pref.page_number)

    if False in scan_list:  # some scanned, but not all.
        # set group to "unscanned"
        with plomdb.atomic():
            gref.scanned = False
            gref.save()
        return False
    # all test pages scanned (or all unscanned), so set things ready to go.
    with plomdb.atomic():
        gref.scanned = True
        gref.save()
        log.info(f"DNMGroup of test {gref.test.test_number} is all scanned.")
    return True


def updateIDGroup(self, idref):
    """Update the ID task when new pages uploaded to IDGroup.
    Recreate the IDpages and check if all scanned, set scanned flag accordingly.
    If group is all scanned then the associated ID-task should be set to "todo".
    Note - be careful when group was auto-IDd (which happens when the associated user = HAL) - then we don't change anything.
    Note - this should only be triggered by a tpage upload.
    Also note - hwscan creates required tpage for the IDgroup on upload of pages.

    args:
        idref (IDGroup): A reference to the IDGroup of the test.
    returns:
        bool: True - the IDGroup (which is a single page) is scanned, False otherwise.
    """

    # grab associated parent group
    gref = idref.group
    # first remove any old dnmpages - there is at most one.
    for pref in idref.idpages:
        pref.delete_instance()
    # now rebuild them, keeping track of which are scanned or not
    # only have to check tpages - not hw or extra pages.
    # note - there is exactly one
    pref = gref.tpages[0]
    if pref.scanned:
        IDPage.create(idgroup=idref, image=pref.image, order=pref.page_number)
    else:
        with plomdb.atomic():
            gref.scanned = False
            gref.save()
        return False  # not yet completely present - no updated needed.

    # all test ID pages present, and group cleaned, so set things ready to go.
    with plomdb.atomic():
        # the group is now scanned
        gref.scanned = True
        gref.save()
        # we'll need a ref to the test
        tref = idref.test
        # if IDGroup belongs to HAL then don't mess with it - was auto IDd.
        if idref.user == User.get(name="HAL"):
            log.info(f"IDGroup of test {tref.test_number} is present and already IDd.")
        else:
            # need to clean it off and set it ready to do.
            idref.status = "todo"
            idref.user = None
            idref.time = datetime.now()
            idref.student_id = None
            idref.student_name = None
            idref.identified = False
            idref.time = datetime.now()
            idref.save()
            tref.identified = False
            tref.save()
            log.info(
                f"IDGroup of test {tref.test_number} is updated and ready to be identified."
            )

    return True


def buildUpToDateAnnotation(self, qref):
    """The pages under the given qgroup have changed, so the old annotations need
    to be flagged as outdated, and a new up-to-date annotation needs to be instantiated.
    This also sets the parent qgroup and test as unmarked, and the qgroup status is
    set to an empty string, "",ie not ready to go.

    If only the zeroth annotation present, then the question is untouched. In that case,
    recycle the zeroth annotation rather than replacing it. Do this so that when we do
    initial upload we don't create new annotations on each uploaded page.

    args:
        qref (QGroup): reference to the QGroup being updated.
    returns:
        nothing.
    """

    tref = qref.test
    HAL_ref = User.get(name="HAL")
    # first flag older annotations as outdated
    # and then create a new annotation or
    # recycle if only zeroth annotation present - question untouched.
    # and - of course, be careful if there are no annotations yet (eg on build)
    with plomdb.atomic():
        if len(qref.annotations) > 1:
            for aref in qref.annotations:
                aref.outdated = True
                aref.save()
            # now create a new latest annotation
            new_ed = qref.annotations[-1].edition + 1
            aref = Annotation.create(qgroup=qref, edition=new_ed, user=HAL_ref)
        else:  # only zeroth annotation is present - recycle it.
            aref = qref.annotations[0]
            # clean off its old pages
            for pref in aref.apages:
                pref.delete_instance()
            # we'll replace them in a moment.

        # Add the relevant pages to the new annotation
        ord = 0
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
        # set the integrity_check string to a UUID
        aref.integrity_check = uuid.uuid4().hex
        aref.save()
        # now set the parent group and test as unmarked, with status as blank
        qref.user = None
        qref.marked = False
        qref.status = ""
        qref.save()
        tref.marked = False
        tref.save()

    log.info(
        f"Old annotations for qgroup {qref.question} for test {tref.test_number} are now outdated and a new annotation has been created."
    )


def updateQGroup(self, qref):
    """A new page has been uploaded to the test, so we have to update the
    question-group and its annotations.
    Checks to see if the group has sufficient pages present and the scanned flag
    is set accordingly (strictly speaking set in the parent 'group' not in the qgroup itself).

    The updates to the annotations are done by an auxiliary function. Older annotations are
    now out-of-date and get flagged as such by that aux function.

    args:
        qref (QGroup): a reference to the QGroup to be updated
    returns:
        bool: True means that the qgroup is ready (ie all tpages present, or hwpages present).
              False means that either that the group is missing some (but not all) tpages,
                or no tpages and no hwpages.
    """
    # first set old annotations as out-of-date and,
    # create a new up-to-date annotation, and
    # set parent test/qgroup as unmarked with status blank.
    self.buildUpToDateAnnotation(qref)
    # now check if the group is ready by looking at pages.
    gref = qref.group
    # TODO = if extra pages present in test, then test is not ready.

    # when some but not all TPages present - not ready
    # when 0 pages present - not ready
    # otherwise ready.
    scan_list = [p.scanned for p in gref.tpages]  # list never zero length.
    if True in scan_list:  # some tpages scanned.
        # some tpages unscanned - definitely not ready to go.
        if False in scan_list:
            log.info("Group {} is only half-scanned - not ready".format(gref.gid))
            with plomdb.atomic():
                gref.scanned = False
                gref.save()
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
            with plomdb.atomic():
                gref.scanned = False
                gref.save()
            return False
        else:
            pass  # no unscanned tpages, but not hw pages - so ready to go.

    # If we get here - we are ready to go.
    with plomdb.atomic():
        gref.scanned = True
        gref.save()
        qref.status = "todo"
        qref.save()
        log.info(
            "QGroup {} of test {} is ready to be marked.".format(
                qref.question, qref.test.test_number
            )
        )
    return True


def updateGroupAfterChange(self, gref):
    """Check the type of the group and update accordingly.
    return success/failure of that update.

    args:
        gref (Group): A reference to the group to be updated.
    returns:
        bool: True - the group is ready (ie required pages present), otherwise False.
    """
    if gref.group_type == "i":
        return self.updateIDGroup(gref.idgroups[0])
    elif gref.group_type == "d":
        return self.updateDNMGroup(gref.dnmgroups[0])
    elif gref.group_type == "q":
        return self.updateQGroup(gref.qgroups[0])
    else:
        raise ValueError("Tertium non datur: should never happen")


def checkTestScanned(self, tref):
    """Check if all groups scanned.

    args:
        tref (Test): A reference to the test being checked.
    returns:
        bool: True - all groups scanned (and so ready), False otherwise.
    """

    for gref in tref.groups:
        if gref.group_type == "q":
            if not gref.scanned:
                log.info(
                    "Group {} of test {} is not scanned - test not ready.".format(
                        gref.gid, tref.test_number
                    )
                )
                return False
        elif gref.group_type == "d":
            if not gref.scanned:
                log.info(
                    "DNM Group {} of test {} is not scanned - test not ready.".format(
                        gref.gid, tref.test_number
                    )
                )
                return False
        elif gref.group_type == "i":
            if gref.idgroups[0].identified:
                log.info(
                    "ID Group {} of test {} is identified".format(
                        gref.gid, tref.test_number
                    )
                )
            if not gref.scanned:
                log.info(
                    "ID Group {} of test {} is not scanned - test not ready.".format(
                        gref.gid, tref.test_number
                    )
                )
                return False
    return True


def get_groups_using_image(self, img_ref):
    """Get all groups that use the given image in an not-outdated annotation.
    Note that the image may still be attached to a tpage/hwpage/expage, but if that
    page has been removed then it will no longer be attached to one of these and so not
    directly attached to a group. Hence this function searches for annotations that
    use the image (via an apage) and then finds the associated parent qgroup and
    grand-parent group.

    args:
        img_ref (Image): a reference to the image
    returns:
        set(Group): the set of groups that make use of that image in an annotation.
    """

    groups_to_update = set()
    for apage_ref in img_ref.apages:
        annot_ref = apage_ref.annotation
        if not annot_ref.outdated:
            groups_to_update.add(annot_ref.qgroup.group)
    return groups_to_update


def updateTestAfterChange(self, tref, group_refs=None):
    """The given test has changed (page upload/delete) and so its groups need to be updated.
    When a list or set of group references are passed, just those groups are updated, otherwise
    all groups updated. When a group is updated, it is checked to see if it is ready (ie sufficient
    pages present) and any existing work is reset (ie any existing annotations are marked as outdated).
    After group updates done, the test's scanned flag set accordingly (ie true when all groups scanned
    and false otherwise).

    args:
        tref (Test): reference to the test that needs to be updated after one of its pages has been changed.
        group_refs (list or set of Group): If this is absent then all the groups of the test are updated
        (and so the corresponding tasks reset), otherwise just those groups are updated.
    """
    # if group_refs supplied then update just those groups
    # otherwise update all the groups in the test
    if not group_refs:
        group_refs = tref.groups

    for gref in group_refs:
        self.updateGroupAfterChange(gref)

    # now make sure the whole thing is scanned.
    if self.checkTestScanned(tref):
        # set the test as scanned
        with plomdb.atomic():
            tref.scanned = True
            log.info("Test {} is scanned".format(tref.test_number))
            tref.save()
    else:
        # set the test as unscanned
        with plomdb.atomic():
            tref.scanned = False
            log.info("Test {} is not completely scanned".format(tref.test_number))
            tref.save()


def removeScannedTestPage(self, test_number, page_number):
    """Remove a single scanned test-page."""
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", f"Cannot find test {test_number}"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]
    pref = tref.tpages.where(TPage.page_number == page_number).first()
    if pref is None:
        log.warn(f"Cannot find t-page {page_number} of test {test_number}.")
        return [False, "unknown"]

    if not pref.scanned:
        log.warn(
            f"T-Page {page_number} of test {test_number} is not scanned - cannot remove."
        )
        return [False, "unscanned"]
    iref = pref.image
    gref = pref.group
    with plomdb.atomic():
        DiscardedPage.create(
            image=iref,
            reason=f"Discarded test-page scan from test {test_number} page {page_number}",
        )
        # Don't delete the actual test-page, just set its image to none and scanned to false
        pref.image = None
        pref.scanned = False
        pref.save()
    # Update the group to which this tpage officially belongs, but also look to see if it had been
    # attached to any annotations, in which case update those too.
    groups_to_update = self.get_groups_using_image(iref)
    groups_to_update.add(gref)
    self.updateTestAfterChange(tref, group_refs=groups_to_update)
    log.info(f"Removed t-page {page_number} of test {test_number} and updated test.")
    return [True, f"Removed tpage-{page_number} form test {test_number}."]


def removeScannedHWPage(self, test_number, question, order):
    """Remove a single scanned hw-page."""
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", f"Cannot find test {test_number}"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    qref = tref.qgroups.where(QGroup.question == question).first()
    if qref is None:
        log.warn(f"Cannot find question {question} - cannot remove page {order}")
        return [False, "unknown"]
    gref = qref.group
    pref = gref.hwpages.where(HWPage.order == order).first()
    if pref is None:
        log.warn(f"Cannot find hw-page {question}.{order} of test {test_number}.")
        return [False, "unknown"]
    # create the discard page
    iref = pref.image
    gref = pref.group
    with plomdb.atomic():
        DiscardedPage.create(
            image=iref,
            reason=f"Discarded hw-page {question}.{order} scan from test {test_number}",
        )
        # now delete that hwpage
        pref.delete_instance()
    # Update the group to which this tpage officially belongs, but also look to see if it had been
    # attached to any annotations, in which case update those too.
    groups_to_update = self.get_groups_using_image(iref)
    groups_to_update.add(qref.group)
    # update the test
    self.updateTestAfterChange(tref, group_refs=groups_to_update)
    log.info(
        f"Removed hwpage {question}.{order} of test {test_number} and updated test."
    )
    return [True, f"Removed hwpage {question}.{order} form test {test_number}."]


def removeScannedEXPage(self, test_number, question, order):
    """Remove a single scanned extra-page."""
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", f"Cannot find test {test_number}"]
    # check if all owners of tasks in that test are logged out.
    owners = self.testOwnersLoggedIn(tref)
    if owners:
        return [False, "owners", owners]

    qref = tref.qgroups.where(QGroup.question == question).first()
    if qref is None:
        log.warn(f"Cannot find question {question} - cannot remove page {order}")
        return [False, "unknown"]
    gref = qref.group
    pref = gref.expages.where(EXPage.order == order).first()
    if pref is None:
        log.warn(f"Cannot find extra-page {question}.{order} of test {test_number}.")
        return [False, "unknown"]
    # create the discard page
    iref = pref.image
    gref = pref.group
    with plomdb.atomic():
        DiscardedPage.create(
            image=iref,
            reason=f"Discarded ex-page {question}.{order} scan from test {test_number}",
        )
        # now delete that hwpage
        pref.delete_instance()
    # Update the group to which this tpage officially belongs, but also look to see if it had been
    # attached to any annotations, in which case update those too.
    groups_to_update = self.get_groups_using_image(iref)
    groups_to_update.add(gref)
    self.updateTestAfterChange(tref, group_refs=groups_to_update)
    log.info(
        f"Removed expage {question}.{order} of test {test_number} and updated test."
    )
    return [True, f"Removed expage {question}.{order} form test {test_number}."]


def removeAllScannedPages(self, test_number):
    # return the give test to the pre-upload state.
    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return [False, "testError", f"Cannot find test {test_number}"]
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
        # finally - clean off the scanned and used flags
        tref.scanned = False
        tref.used = False
        tref.save()
    # update all the groups - don't pass any group-references
    self.updateTestAfterChange(tref)
    return [True, "Test {} wiped clean".format(test_number)]


# some bundle related stuff
def listBundles(self):
    """Returns a list of bundles in the database

    Args: None

    Returns:
        List (dict). One for each bundle. Each dict contains three
            key-value pairs: "name", "md5sum" and "numberOfPages".
            If no bundles in the system, then it returns an empty list.
    """

    bundle_info = []
    for bref in Bundle.select():
        bundle_info.append(
            {
                "name": bref.name,
                "md5sum": bref.md5sum,
                "numberOfPages": len(bref.images),
            }
        )
    return bundle_info


# ==== Bundle associated functions


def getBundleFromImage(self, file_name):
    """
    From the given filename get the bundle name the image is in.
    Returns [False, message] or [True, bundle-name]
    """
    iref = Image.get_or_none(Image.file_name == file_name)
    if iref is None:
        return [False, "No image with that file name"]
    return [True, iref.bundle.name]


def getImagesInBundle(self, bundle_name):
    """Get list of images in the given bundle.
    Returns [False, message] or [True imagelist] where
    imagelist is list of triples (filename, md5sum, bundle order)
    ordered by bundle_order.
    """
    bref = Bundle.get_or_none(Bundle.name == bundle_name)
    if bref is None:
        return [False, "No bundle with that name"]
    images = []
    for iref in bref.images.order_by(Image.bundle_order):
        images.append((iref.file_name, iref.md5sum, iref.bundle_order))
    return [True, images]


def getPageFromBundle(self, bundle_name, bundle_order):
    """Get the image at position bundle_order from bundle of given name"""
    bref = Bundle.get_or_none(Bundle.name == bundle_name)
    if bref is None:
        return [False]
    iref = Image.get_or_none(Image.bundle == bref, Image.bundle_order == bundle_order)
    if iref is None:
        return [False]
    else:
        return [True, iref.file_name]
