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
        newName = "pages/unknownPages/" + prefix + unique + ".png"
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
    rval = self.DB.replaceMissingPage(
        testNumber, pageNumber, version, originalName, newName, md5
    )
    # if move successful then actually move file into place, else delete it
    if rval[0]:
        shutil.move(originalName, newName)
    else:
        os.unlink(originalName)
    return rval


def getPageImage(self, testNumber, pageNumber, version):
    return self.DB.getPageImage(testNumber, pageNumber, version)


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


def getTestImages(self, testNumber):
    return self.DB.getTestImages(testNumber)


def checkPage(self, testNumber, pageNumber):
    return self.DB.checkPage(testNumber, pageNumber)


def removeUnknownImage(self, fname):
    newFilename = "pages/discardedPages/" + os.path.split(fname)[1]
    if self.DB.removeUnknownImage(fname, newFilename):
        shutil.move(fname, newFilename)
        return [True]
    else:
        return [False]


def removeCollidingImage(self, fname):
    newFilename = "pages/discardedPages/" + os.path.split(fname)[1]
    if self.DB.removeCollidingImage(fname, newFilename):
        shutil.move(fname, newFilename)
        return [True]
    else:
        return [False]


def unknownToTestPage(self, fname, test, page, rotation):
    # first rotate the page
    subprocess.run(
        ["mogrify", "-quiet", "-rotate", rotation, fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )
    # checkpage returns
    # -- [False] no such page exists
    # -- [True, version] page exists but hasnt been scanned
    # -- or [True, version, image] page exists and has been scanned
    val = self.DB.checkPage(test, page)
    if val[0]:
        if len(val) == 3:
            # existing page in place - create a colliding page
            newFilename = "pages/collidingPages/" + os.path.split(fname)[1]
            print("Collide = {}".format(newFilename))
            if self.DB.moveUnknownToCollision(fname, newFilename, test, page)[0]:
                shutil.move(fname, newFilename)
                return [True, "collision"]
        else:
            newFilename = "pages/originalPages/" + os.path.split(fname)[1]
            print("Original = {}".format(newFilename))
            if self.DB.moveUnknownToPage(fname, newFilename, test, page)[0]:
                shutil.move(fname, newFilename)
                return [True, "testPage"]
    else:  # some sort of problem occurred
        return [False]


def unknownToExtraPage(self, fname, test, question, rotation):
    newFilename = "pages/originalPages/" + os.path.split(fname)[1]
    rval = self.DB.moveExtraToPage(fname, newFilename, test, question)
    # returns [True, [file1,file2,..]] or [False]
    # the files are annotations to be deleted
    if rval[0]:
        # move file into place
        shutil.move(fname, newFilename)
        # moved successfully. now rotate the page
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", rotation, newFilename],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
        # clean up any annotation files
        for fn in rval[1]:
            os.unlink(fn)
    else:
        return [False]
    return [True]


def removeScannedPage(self, testNumber, pageNumber, version):
    # the scanned page moves to a discardedPage
    # any annotations are deleted.
    fname = self.DB.fileOfScannedPage(testNumber, pageNumber, version)
    # returns either None or [filename, originalName, md5sum]
    if fname is None:
        return [False, "Cannot find page"]
    # need to create a discardedPage object and move files
    newFilename = "pages/discardedPages/" + os.path.split(fname)[1]
    rval = self.DB.removeScannedPage(fname, newFilename)
    if rval[0]:
        shutil.move(fname, newFilename)
        for fn in rval[1]:
            os.unlink(fn)
        return [True]
    else:
        return [False]


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


def discardToUnknown(self, fname):
    newFilename = "pages/unknownPages/" + os.path.split(fname)[1]
    if self.DB.moveDiscardToUnknown(fname, newFilename):
        shutil.move(fname, newFilename)
        return [True]
    else:
        return [False]
