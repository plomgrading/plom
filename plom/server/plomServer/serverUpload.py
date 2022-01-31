# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

import hashlib
import logging
import os
import shutil
import subprocess
import uuid

from plom.server import pageNotSubmitted


log = logging.getLogger("server")


def doesBundleExist(self, bundle_file, md5):
    return self.DB.doesBundleExist(bundle_file, md5)


def createNewBundle(self, bundle_file, md5):
    return self.DB.createNewBundle(bundle_file, md5)


def listBundles(self):
    return self.DB.listBundles()


def sidToTest(self, student_id):
    return self.DB.sidToTest(student_id)


def addTestPage(self, t, p, v, fname, image, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    prefix = "t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = "pages/originalPages/" + prefix + unique + ext
        if not os.path.isfile(newName):
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
    return self.createIDPageForHW(sid)


def createIDPageForHW(self, sid):
    # ask DB if that SID belongs to a test and if that has an ID page
    val = self.DB.doesHWHaveIDPage(sid)
    # returns [False, 'unknown'], [False, 'noid', test_number, student_name], or
    # [True, 'idpage', test_number, student_name]
    if val[0]:  # page already has an idpage, so we can just return
        log.debug(f"HW from sid {sid} is test {val[2]} - already has an ID Page.")
        return True
    if val[1] == "unknown":
        log.debug(f"The sid {sid} does not correspond to any test in the DB.")
        return False
    test_number = val[2]
    student_name = val[3]
    log.debug(f"HW from sid {sid} is test {val[2]}, {student_name} - creating ID page.")
    return autogenerateIDPage(self, test_number, sid, student_name)


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


def addHWPage(self, sid, q, o, fname, image, md5o, bundle, bundle_order):
    # Create an ID page and DNM for that HW if it is needed
    self.createIDPageForHW(sid)
    self.createDNMPagesForHW(sid)

    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    qstr = "_".join([str(x) for x in q])
    prefix = "s{}q{}o{}".format(sid, qstr, o)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = "pages/originalPages/" + prefix + unique + ext
        if not os.path.isfile(newName):
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
        newName = "pages/unknownPages/" + prefix + unique + ext
        if not os.path.isfile(newName):
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
        newName = "pages/collidingPages/" + prefix + unique + ext
        if not os.path.isfile(newName):
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
    # TODO - we should probably have some sort of try/except around this.
    pageNotSubmitted.build_test_page_substitute(testNumber, pageNumber, version)
    # produces a file "pns.<testNumber>.<pageNumber>.<ver>.png"
    originalName = "pns.{}.{}.{}.png".format(testNumber, pageNumber, version)
    prefix = "pages/originalPages/pns.{}p{}v{}".format(
        str(testNumber).zfill(4), str(pageNumber).zfill(2), version
    )
    # make a non-colliding name
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    # compute md5sum and put into database
    with open(originalName, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    rval = self.DB.replaceMissingTestPage(
        testNumber, pageNumber, version, originalName, newName, md5
    )
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def replaceMissingDNMPage(self, testNumber, pageNumber):
    pageNotSubmitted.build_dnm_page_substitute(testNumber, pageNumber)
    # produces a file "dnm.<testNumber>.<pageNumber>.png"
    originalName = "dnm.{}.{}.png".format(testNumber, pageNumber)
    prefix = "pages/originalPages/dnm.{}p{}".format(
        str(testNumber).zfill(4), str(pageNumber).zfill(2)
    )
    # make a non-colliding name
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    # compute md5sum and put into database
    with open(originalName, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    # all DNM are test pages with version 1, so recycle the missing test page function
    rval = self.DB.replaceMissingTestPage(
        testNumber, pageNumber, 1, originalName, newName, md5
    )
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def autogenerateIDPage(self, testNumber, student_id, student_name):
    # Do not call this directly, it should be called by createIDPageForHW
    pageNotSubmitted.build_generated_id_page_for_student(student_id, student_name)

    # produces a file "autogen.<sid>.png"
    originalName = "autogen.{}.png".format(student_id)
    prefix = "pages/originalPages/autogen.{}.{}".format(
        str(testNumber).zfill(4), student_id
    )
    # make a non-colliding name
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    # compute md5sum and put into database
    with open(originalName, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    # all ID are test pages with version 1, so recycle the missing test page function
    # get the id-page's pagenumber from the spec
    pg = self.testSpec["idPage"]
    rval = self.DB.replaceMissingTestPage(testNumber, pg, 1, originalName, newName, md5)
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def getTPageImage(self, testNumber, pageNumber, version):
    return self.DB.getTPageImage(testNumber, pageNumber, version)


def getHWPageImage(self, testNumber, question, order):
    return self.DB.getHWPageImage(testNumber, question, order)


def getEXPageImage(self, testNumber, question, order):
    return self.DB.getEXPageImage(testNumber, question, order)


def getUnknownImage(self, fname):
    return self.DB.getUnknownImage(fname)


def getDiscardImage(self, fname):
    return self.DB.getDiscardImage(fname)


def getCollidingImage(self, fname):
    return self.DB.getCollidingImage(fname)


def getUnknownPageNames(self):
    return self.DB.getUnknownPageNames()


def getDiscardNames(self):
    return self.DB.getDiscardNames()


def getCollidingPageNames(self):
    return self.DB.getCollidingPageNames()


def getQuestionImages(self, testNumber, questionNumber):
    return self.DB.getQuestionImages(testNumber, questionNumber)


def getAllTestImages(self, testNumber):
    return self.DB.getAllTestImages(testNumber)


def checkTPage(self, testNumber, pageNumber):
    return self.DB.checkTPage(testNumber, pageNumber)


def removeUnknownImage(self, file_name):
    return self.DB.removeUnknownImage(file_name)


def discardToUnknown(self, file_name):
    return self.DB.moveDiscardToUnknown(file_name)


def removeCollidingImage(self, file_name):
    return self.DB.removeCollidingImage(file_name)


def unknownToTestPage(self, file_name, test, page, rotation):
    status, code, msg = self.DB.moveUnknownToTPage(file_name, test, page)
    if status:
        # rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, file_name],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
        return (True, "testPage", None)

    if not status and code != "scanned":
        return (status, code, msg)

    # existing page in place - create a colliding page
    status, code, msg = self.DB.moveUnknownToCollision(file_name, test, page)
    if status:
        # rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, file_name],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
        return (True, "collision", None)
    return (status, code, msg)


def unknownToExtraPage(self, fname, test, question, rotation):
    rval = self.DB.moveUnknownToExtraPage(fname, test, question)
    if rval[0]:
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    return rval


def unknownToHWPage(self, fname, test, questions, rotation):
    rval = self.DB.moveUnknownToHWPage(fname, test, questions)
    if rval[0]:
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    return rval


def removeAllScannedPages(self, test_number):
    return self.DB.removeAllScannedPages(test_number)


def removeSinglePage(self, test_number, page_name):
    # page name should be "t.n" or "h.q.o" or "e.q.o"
    splut = page_name.split(".")
    if len(splut) not in [2, 3]:
        return [False, "invalid"]
    if splut[0] == "t":
        try:
            page_number = int(splut[1])
        except ValueError:
            return [False, "page name invalid"]
        return self.DB.removeScannedTestPage(test_number, page_number)
    elif splut[0] == "h":
        try:
            question = int(splut[1])
            order = int(splut[2])
        except ValueError:
            return [False, "page name invalid"]
        return self.DB.removeScannedHWPage(test_number, question, order)
    elif splut[0] == "e":
        try:
            question = int(splut[1])
            order = int(splut[2])
        except ValueError:
            return [False, "page name invalid"]
        return self.DB.removeScannedEXPage(test_number, question, order)
    else:
        return [False, "invalid"]


def collidingToTestPage(self, file_name, test, page, version):
    return self.DB.moveCollidingToTPage(file_name, test, page, version)


def replaceMissingHWQuestion(self, sid, test, question):
    if sid is None:
        # compute sid from test-number
        if test is None:
            return [False, "Need at least one of sid or test"]
        rval = self.DB.getSIDFromTest(test)
        if rval[0]:
            sid = rval[1]
        else:
            return rval

    # TODO - we should probably have some sort of try/except around this.
    pageNotSubmitted.build_homework_question_substitute(sid, question)
    # produces a file "pns.<sid>.<pageNumber>.<ver>.png"
    originalName = "qns.{}.{}.png".format(sid, question)
    prefix = "pages/originalPages/pns.{}q{}".format(sid, question)
    # make a non-colliding name
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
        newName = "pages/originalPages/" + prefix + unique + ".png"
    # compute md5sum and put into database
    with open(originalName, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    # now try to put it into place
    rval = self.DB.replaceMissingHWQuestion(sid, question, originalName, newName, md5)
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def getBundleFromImage(self, file_name):
    return self.DB.getBundleFromImage(file_name)


def getImagesInBundle(self, bundle_name):
    return self.DB.getImagesInBundle(bundle_name)


def getPageFromBundle(self, bundle_name, bundle_order):
    return self.DB.getPageFromBundle(bundle_name, bundle_order)


##

##
