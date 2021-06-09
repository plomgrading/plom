# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

import hashlib
import os
import shlex
import shutil
import subprocess
import uuid
import logging

from plom.server import pageNotSubmitted


log = logging.getLogger("server")


def doesBundleExist(self, bundle_file, md5):
    return self.DB.doesBundleExist(bundle_file, md5)


def createNewBundle(self, bundle_file, md5):
    return self.DB.createNewBundle(bundle_file, md5)


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
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def addHWPage(self, sid, q, o, fname, image, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    if isinstance(q, list):
        qstr = "_".join([str(x) for x in q])
    else:
        qstr = str(q)
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
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o
        log.debug("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        log.debug("Did not store page.  From database = {}".format(val[1]))
    return val


def addLPage(self, sid, o, fname, image, md5o, bundle, bundle_order):
    # take extension from the client filename
    base, ext = os.path.splitext(fname)
    # create a filename for the image
    prefix = "s{}o{}".format(sid, o)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = "pages/originalPages/" + prefix + unique + ext
        if not os.path.isfile(newName):
            break
    val = self.DB.uploadLPage(sid, o, fname, newName, md5o, bundle, bundle_order)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
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
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
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
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
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
        newName = "pages/originalPages/" + prefix + unique + ".png"
    # compute md5sum and put into database
    md5 = hashlib.md5(open(originalName, "rb").read()).hexdigest()
    # now try to put it into place
    rval = self.DB.replaceMissingTestPage(
        testNumber, pageNumber, version, originalName, newName, md5
    )
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


def getLPageImage(self, testNumber, order):
    return self.DB.getLPageImage(testNumber, order)


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
    # checkpage returns
    # -- [False, reason] no such page exists, or owners logged in
    # -- [True, 'unscanned', version] page exists but hasnt been scanned
    # -- or [True, 'collision', version, image] page exists and has been scanned
    val = self.DB.checkTPage(test, page)
    if val[0]:
        # rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, file_name],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
        if len(val) == 4:
            # existing page in place - create a colliding page
            if self.DB.moveUnknownToCollision(file_name, test, page)[0]:
                return [True, "collision"]
            else:
                return [False, "HUH?"]  # this should not happen
        else:
            msg = self.DB.moveUnknownToTPage(file_name, test, page)
            # returns [True] or [False, reason] or [False, "owners", owner_list]
            if msg[0]:
                return [True, "testPage"]
            else:
                return msg

    else:  # some sort of problem occurred
        return val


def unknownToExtraPage(self, fname, test, question, rotation):
    rval = self.DB.moveUnknownToExtraPage(fname, test, question)
    # returns [True] or [False, reason]
    if rval[0]:
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    else:
        return rval
    return [True]


def unknownToHWPage(self, fname, test, question, rotation):
    rval = self.DB.moveUnknownToHWPage(fname, test, question)
    # returns [True] or [False, reason]
    if rval[0]:
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    else:
        return rval
    return [True]


def removeAllScannedPages(self, test_number):
    return self.DB.removeAllScannedPages(test_number)


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
    md5 = hashlib.md5(open(originalName, "rb").read()).hexdigest()
    # now try to put it into place
    rval = self.DB.replaceMissingHWQuestion(sid, question, originalName, newName, md5)
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def processHWUploads(self):
    return self.DB.processUpdatedTests()


def processLUploads(self):
    return self.DB.processUpdatedTests()


def processTUploads(self):
    return self.DB.processUpdatedTests()
