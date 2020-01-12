import hashlib
import os
import shlex
import shutil
import subprocess
import uuid


def addKnownPage(self, t, p, v, fname, image, md5o):
    # create a filename for the image
    prefix = "t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = "pages/originalPages/" + prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    val = self.DB.uploadKnownPage(t, p, v, fname, newName, md5o)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o
        print("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        print("Did not store page")
        print("From database = {}".format(val[1]))
    return val


def addUnknownPage(self, fname, image, md5o):
    # create a filename for the image
    prefix = "unk."
    while True:
        unique = str(uuid.uuid4())[:8]
        newName = "pages/originalPages/" + prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    val = self.DB.uploadUnknownPage(fname, newName, md5o)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o
        print("Storing {} = {}".format(newName, val))
    else:
        print("Did not store page")
        print("From database = {}".format(val[1]))
    return val


def addCollidingPage(self, t, p, v, fname, image, md5o):
    # create a filename for the image
    prefix = "col.t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), v)
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = "pages/collidingPages/" + prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
    val = self.DB.uploadCollidingPage(t, p, v, fname, newName, md5o)
    if val[0]:
        with open(newName, "wb") as fh:
            fh.write(image)
        md5n = hashlib.md5(open(newName, "rb").read()).hexdigest()
        assert md5n == md5o
        print("Storing {} as {} = {}".format(prefix, newName, val))
    else:
        print("Did not store page")
        print("From database = {}".format(val[1]))
    return val


def replaceMissingPage(self, testNumber, pageNumber, version):
    rval = self.DB.checkTestPageUnscanned(testNumber, pageNumber, version)
    if not (rval[0] and rval[1]):
        return rval
    # build a "pageNotSubmitted page"
    cmd = "python3 ./pageNotSubmitted.py {} {} {}".format(
        testNumber, pageNumber, version
    )
    subprocess.check_call(shlex.split(cmd))
    # produces a file "pns.<testNumber>.<pageNumber>.<ver>.png"
    originalName = "pns.{}.{}.{}.png".format(testNumber, pageNumber, version)
    prefix = "pages/originalPages/pns.{}p{}v{}".format(
        str(testNumber).zfill(4), str(pageNumber).zfill(2), version
    )
    while True:
        unique = "." + str(uuid.uuid4())[:8]
        newName = prefix + unique + ".png"
        if not os.path.isfile(newName):
            break
        newName = "pages/originalPages/" + prefix + unique + ".png"

    md5 = hashlib.md5(open(originalName, "rb").read()).hexdigest()
    val = self.DB.replaceMissingPage(
        testNumber, pageNumber, version, originalName, newName, md5
    )
    shutil.move(originalName, newName)
    return val


def getPageImage(self, testNumber, pageNumber, version):
    return self.DB.getPageImage(testNumber, pageNumber, version)


def getUnknownImage(self, fname):
    return self.DB.getUnknownImage(fname)


def getCollidingImage(self, fname):
    return self.DB.getCollidingImage(fname)


def getUnknownPageNames(self):
    return self.DB.getUnknownPageNames()


def getCollidingPageNames(self):
    return self.DB.getCollidingPageNames()


def getQuestionImages(self, testNumber, questionNumber):
    return self.DB.getQuestionImages(testNumber, questionNumber)


def getTestImages(self, testNumber):
    return self.DB.getTestImages(testNumber)


def checkPage(self, testNumber, pageNumber):
    return self.DB.checkPage(testNumber, pageNumber)


def removeUnknownImage(self, fname):
    fnon = self.DB.checkUnknownImage(fname)
    # returns either None or [filename, originalName, md5sum]
    if fnon is None:
        return [False, "Cannot find page"]
    # need to create a discardedPage object and move files
    newFilename = "pages/discardedPages/" + os.path.split(fnon[0])[1]
    shutil.move(fnon[0], newFilename)
    self.DB.createDiscardedPage(
        fnon[1],  # originalName
        newFilename,
        fnon[2],  # md5sum
        "Manager removed page",
        "",
    )
    rval = self.DB.removeUnknownImage(fname)
    return [True]


def removeCollidingImage(self, fname):
    fnon = self.DB.checkCollidingImage(fname)
    # returns either None or [filename, originalName, md5sum]
    if fnon is None:
        return [False, "Cannot find page"]
    # need to create a discardedPage object and move files
    newFilename = "pages/discardedPages/" + os.path.split(fnon[0])[1]
    shutil.move(fnon[0], newFilename)
    self.DB.createDiscardedPage(
        fnon[1],  # originalName
        newFilename,
        fnon[2],  # md5sum
        "Manager removed page",
        "",
    )
    rval = self.DB.removeCollidingImage(fname)
    return [True]


def unknownToTestPage(self, fname, test, page, rotation):
    # first rotate the page
    subprocess.run(
        ["mogrify", "-quiet", "-rotate", rotation, fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )
    if self.DB.checkPage(test, page)[0]:
        # existing page in place - create a colliding page
        newFilename = "pages/collidingPages/" + os.path.split(fnon[0])[1]
        if self.DB.moveUnknownToCollision(fname, newFilename, test, page)[0]:
            shutil.move(fname, newFilename)
            return [True, "collision"]
    else:
        if self.DB.moveUnknownToPage(fname, test, page)[0]:
            return [True, "testPage"]
    # some sort of problem occurred
    return [False]


def unknownToExtraPage(self, fname, test, question, rotation):
    if self.DB.moveExtraToPage(fname, test, question)[0]:
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
    else:
        return [False]
    return [True]


def removeScannedPage(self, testNumber, pageNumber, version):
    # the scanned page moves to a discardedPage
    # any annotations are deleted.
    fnon = self.DB.checkScannedPage(testNumber, pageNumber, version)
    # returns either None or [filename, originalName, md5sum]
    if fnon is None:
        return [False, "Cannot find page"]
    # need to create a discardedPage object and move files
    newFilename = "pages/discardedPages/" + os.path.split(fnon[0])[1]
    shutil.move(fnon[0], newFilename)
    self.DB.createDiscardedPage(
        fnon[1],  # originalName
        newFilename,
        fnon[2],  # md5sum
        "Manager removed page",
        "t{}p{}v{}".format(testNumber, pageNumber, version),
    )
    # clean up any annotated files
    rval = self.DB.removeScannedPage(testNumber, pageNumber, version)
    for fn in rval:
        os.unlink(fn)

    return [True]


def collidingToTestPage(self, fname, test, page, version):
    # first remove the current scanned page
    if not self.removeScannedPage(test, page, version)[0]:
        return [False]
    # now move the collision into place
    newFilename = "pages/originalPages/" + os.path.split(fname)[1]
    if self.DB.moveCollidingToPage(fname, newFilename, test, page, version)[0]:
        shutil.move(fname, newFilename)
        return [True]
    # some sort of problem occurred
    return [False]
