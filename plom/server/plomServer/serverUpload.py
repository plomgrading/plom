# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Joey Shi

import hashlib
import logging
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from plom.server import pageNotSubmitted


log = logging.getLogger("server")


def doesBundleExist(self, *args, **kwargs):
    return self.DB.doesBundleExist(*args, **kwargs)


def createNewBundle(self, *args, **kwargs):
    return self.DB.createNewBundle(*args, **kwargs)


def listBundles(self):
    return self.DB.listBundles()


def sidToTest(self, *args, **kwargs):
    return self.DB.sidToTest(*args, **kwargs)


def addTestPage(self, t, p, v, fname, image, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    prefix = "t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = Path("pages/originalPages") / (prefix + unique + ext)
        if not newName.exists():
            break
    val = self.DB.uploadTestPage(t, p, v, fname, newName, md5o, bundle, bundle_order)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        with open(newName, "rb") as fh:
            md5n = hashlib.md5(fh.read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def replaceMissingIDPage(self, test_number):
    val = self.DB.getSIDFromTest(test_number)
    if val[0] is False:
        return [False, "unknown"]
    sid = val[1]
    # TODO: returns True/False/None
    # Also: this looks broken, no student_name arg: Issue #2461
    return self.createIDPageForHW(sid)


def createIDPageForHW(self, sid, student_name):
    # first check if that sid has been used to ID a test.
    used, why, test_number = self.DB.is_sid_used(sid)
    if used is False:
        log.warning(
            f"The sid {sid} does not correspond to any test or prediction in the DB."
        )
        return False
    if (
        why == "identified"
    ):  # the sid has been used to identify a test, so ID page exists.
        log.warning(
            f"HW from sid {sid} is test {test_number} - already has an ID Page."
        )
        return True
    # so at this point we have a predicted ID, so we need to make an ID page and identify the test.
    # to identify the test we need to grab name from classlist.
    log.warning(
        f"HW from {sid} {student_name} is test {test_number} - creating ID page and identifying test."
    )
    # this makes a auto-gen id page and uploads it into the db
    rval = autogenerateIDPage(self, test_number, sid, student_name)
    # TODO: rather fragile error handling
    assert rval[0]
    assert rval[1] == "success"
    # now identify the test
    log.warning("About to id it")
    self.DB.ID_id_paper(test_number, "scanner", sid, student_name, checks=False)
    log.warning("Hopefully have id'd it.")


def createDNMPagesForHW(self, sid):
    # ask DB if that SID belongs to a test and if that has DNM Pages
    val = self.DB.sidToTest(sid)
    if val[0] is False:
        log.debug(f"The sid {sid} does not correspond to any test in the DB.")
        return False
    test_number = val[1]
    val = self.DB.getMissingDNMPages(test_number)
    # return [False, "unknown"] or [True, [list of unscanned tpages from the dnm group]]
    if val[0] is False:
        log.debug(f"Test {test_number} does not correspond to a test in the database")
        return False
    needed_dnm_pages = val[1]
    for page_number in needed_dnm_pages:
        replaceMissingDNMPage(self, test_number, page_number)


def addHWPage(self, sid, student_name, q, o, fname, image, md5o, bundle, bundle_order):
    # Create an ID page and DNM for that HW if it is needed
    # This also "identifies" the corresponding test from data in the prediction list.
    self.createIDPageForHW(sid, student_name)
    self.createDNMPagesForHW(sid)

    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    qstr = "_".join([str(x) for x in q])
    prefix = "s{}q{}o{}".format(sid, qstr, o)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = Path("pages/originalPages") / (prefix + unique + ext)
        if not newName.exists():
            break
    val = self.DB.uploadHWPage(sid, q, o, fname, newName, md5o, bundle, bundle_order)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        with open(newName, "rb") as fh:
            md5n = hashlib.md5(fh.read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def addUnknownPage(self, fname, image, order, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    prefix = "unk."
    while True:
        unique = str(uuid.uuid4())[:8]
        newName = Path("pages/unknownPages") / (prefix + unique + ext)
        if not newName.exists():
            break
    val = self.DB.uploadUnknownPage(fname, newName, order, md5o, bundle, bundle_order)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        with open(newName, "rb") as fh:
            md5n = hashlib.md5(fh.read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} = {}".format(newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def addCollidingPage(self, t, p, v, fname, image, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    prefix = "col.t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = Path("pages/collidingPages") / (prefix + unique + ext)
        if not newName.exists():
            break
    val = self.DB.uploadCollidingPage(
        t, p, v, fname, newName, md5o, bundle, bundle_order
    )
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        with open(newName, "rb") as fh:
            md5n = hashlib.md5(fh.read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def replaceMissingTestPage(self, testNumber, pageNumber, version):
    with tempfile.TemporaryDirectory() as td:
        tmp = pageNotSubmitted.build_test_page_substitute(
            testNumber, pageNumber, version, outdir=td
        )
        prefix = "pns.{}p{}v{}".format(
            str(testNumber).zfill(4), str(pageNumber).zfill(2), version
        )
        # make a non-colliding name
        while True:
            unique = "." + str(uuid.uuid4())[:8]
            newName = Path("pages/originalPages") / (prefix + unique + tmp.suffix)
            if not newName.exists():
                break
        with open(tmp, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        rval = self.DB.replaceMissingTestPage(
            testNumber, pageNumber, version, tmp.name, newName, md5
        )
        # if DB successful then actually move file into place, else GC will cleanup
        if rval[0]:
            shutil.move(tmp, newName)
        return rval


def replaceMissingDNMPage(self, papernum, pagenum):
    with tempfile.TemporaryDirectory() as td:
        tmp = pageNotSubmitted.build_dnm_page_substitute(papernum, pagenum, outdir=td)
        prefix = "dnm.{}p{}".format(str(papernum).zfill(4), str(pagenum).zfill(2))
        # make a non-colliding name
        while True:
            unique = "." + str(uuid.uuid4())[:8]
            newName = Path("pages/originalPages") / (prefix + unique + tmp.suffix)
            if not newName.exists():
                break
        with open(tmp, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        # all DNM are test pages with version 1, so recycle the missing test page function
        rval = self.DB.replaceMissingTestPage(
            papernum, pagenum, 1, tmp.name, newName, md5
        )
        # if DB successful then actually move file into place, else GC will cleanup
        if rval[0]:
            shutil.move(tmp, newName)
        return rval


def autogenerateIDPage(self, testNumber, student_id, student_name):
    # Do not call this directly, it should be called by createIDPageForHW
    with tempfile.TemporaryDirectory() as td:
        tmp = pageNotSubmitted.build_generated_id_page_for_student(
            student_id, student_name, outdir=td
        )
        prefix = "autogen.{}.{}".format(str(testNumber).zfill(4), student_id)
        # make a non-colliding name
        while True:
            unique = "." + str(uuid.uuid4())[:8]
            newName = Path("pages/originalPages") / (prefix + unique + tmp.suffix)
            if not newName.exists():
                break
        with open(tmp, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        # all ID are test pages with version 1, so recycle the missing test page function
        # get the id-page's pagenumber from the spec
        pg = self.testSpec["idPage"]
        rval = self.DB.replaceMissingTestPage(testNumber, pg, 1, tmp.name, newName, md5)
        # if DB successful then actually move file into place, else GC will cleanup
        if rval[0]:
            shutil.move(tmp, newName)
        return rval


def getTPageImage(self, *args, **kwargs):
    return self.DB.getTPageImage(*args, **kwargs)


def getHWPageImage(self, *args, **kwargs):
    return self.DB.getHWPageImage(*args, **kwargs)


def getEXPageImage(self, *args, **kwargs):
    return self.DB.getEXPageImage(*args, **kwargs)


def getCollidingImage(self, *args, **kwargs):
    return self.DB.getCollidingImage(*args, **kwargs)


def getUnknownPages(self):
    return self.DB.getUnknownPages()


def getDiscardedPages(self):
    return self.DB.getDiscardedPages()


def getCollidingPageNames(self):
    return self.DB.getCollidingPageNames()


def checkTPage(self, *args, **kwargs):
    return self.DB.checkTPage(*args, **kwargs)


def removeUnknownImage(self, *args, **kwargs):
    return self.DB.removeUnknownImage(*args, **kwargs)


def discardToUnknown(self, file_name):
    return self.DB.moveDiscardToUnknown(file_name)


def removeCollidingImage(self, file_name):
    return self.DB.removeCollidingImage(file_name)


def unknownToTestPage(self, file_name, test, page, rotation):
    status, code, msg = self.DB.moveUnknownToTPage(file_name, test, page)
    if status:
        # rotate the page
        self.DB.updateImageRotation(file_name, rotation)
        return (True, "testPage", None)

    if not status and code != "scanned":
        return (status, code, msg)

    # existing page in place - create a colliding page
    status, code, msg = self.DB.moveUnknownToCollision(file_name, test, page)
    if status:
        # rotate the page
        self.DB.updateImageRotation(file_name, rotation)
        return (True, "collision", None)
    return (status, code, msg)


def unknownToExtraPage(self, fname, test, question, rotation):
    rval = self.DB.moveUnknownToExtraPage(fname, test, question)
    if rval[0]:
        # moved successfully. now rotate the page
        self.DB.updateImageRotation(fname, rotation)
    return rval


def unknownToHWPage(self, fname, test, questions, rotation):
    rval = self.DB.moveUnknownToHWPage(fname, test, questions)
    if rval[0]:
        # moved successfully. now rotate the page
        self.DB.updateImageRotation(fname, rotation)
    return rval


def removeAllScannedPages(self, test_number):
    return self.DB.removeAllScannedPages(test_number)


def removeSinglePage(self, test_number, page_name):
    """Remove a single page based on a rather cryptic internal page name.

    Returns:
        tuple: `(ok, code, errmsg)` where `ok` is a boolean, `code` is a
        short string for machines to recognize what errors and `errmsg`
        is human-readable error message.  The codes include "invalid",
        "unknown", "unscanned", None (when `ok` is True).
    """
    # page name should be "t.n" or "h.q.o" or "e.q.o"
    splut = page_name.split(".")
    if len(splut) not in [2, 3]:
        return (False, "invalid", f"page name {page_name} invalid")
    if splut[0] == "t":
        try:
            page_number = int(splut[1])
        except ValueError:
            return (False, "invalid", f"page name {page_name} invalid")
        return self.DB.removeScannedTestPage(test_number, page_number)
    elif splut[0] == "h":
        try:
            question = int(splut[1])
            order = int(splut[2])
        except ValueError:
            return (False, "invalid", f"page name {page_name} invalid")
        return self.DB.removeScannedHWPage(test_number, question, order)
    elif splut[0] == "e":
        try:
            question = int(splut[1])
            order = int(splut[2])
        except ValueError:
            return (False, "invalid", f"page name {page_name} invalid")
        return self.DB.removeScannedEXPage(test_number, question, order)
    else:
        return (False, "invalid", f"page name {page_name} invalid")


def collidingToTestPage(self, file_name, test, page, version):
    return self.DB.moveCollidingToTPage(file_name, test, page, version)


def replaceMissingHWQuestion(self, sid, test, question):
    if sid is None:
        # compute sid from test-number
        if test is None:
            return [False, "Need at least one of sid or test"]
        rval = self.DB.getSIDFromTest(test)
        if not rval[0]:
            return rval
        sid = rval[1]

    with tempfile.TemporaryDirectory() as td:
        tmp = pageNotSubmitted.build_homework_question_substitute(
            sid, question, outdir=td
        )
        # TODO: should this be qns?  tmp is...
        prefix = "pns.{}q{}".format(sid, question)
        # make a non-colliding name
        while True:
            unique = "." + str(uuid.uuid4())[:8]
            newName = Path("pages/originalPages") / (prefix + unique + tmp.suffix)
            if not newName.exists():
                break
        with open(tmp, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        # now try to put it into place
        rval = self.DB.replaceMissingHWQuestion(sid, question, tmp.name, newName, md5)
        # if DB successful then actually move file into place, else GC will cleanup
        if rval[0]:
            shutil.move(tmp, newName)
        return rval


def getBundleFromImage(self, *args, **kwargs):
    return self.DB.getBundleFromImage(*args, **kwargs)


def getImagesInBundle(self, *args, **kwargs):
    return self.DB.getImagesInBundle(*args, **kwargs)


def getPageFromBundle(self, *args, **kwargs):
    return self.DB.getPageFromBundle(*args, **kwargs)


def initialiseExamDatabase(self, spec, vmap):
    from plom.db import initialiseExamDatabaseFromSpec

    return initialiseExamDatabaseFromSpec(spec, self.DB, vmap)


def appendTestToExamDatabase(self, *args, **kwargs):
    return self.DB.addSingleTestToDB(*args, **kwargs)


def getPageVersions(self, *args, **kwargs):
    return self.DB.getPageVersions(*args, **kwargs)


def get_question_versions(self, *args, **kwargs):
    return self.DB.get_question_versions(*args, **kwargs)


def get_all_question_versions(self):
    return self.DB.get_all_question_versions()
