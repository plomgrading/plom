import hashlib
import os
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
