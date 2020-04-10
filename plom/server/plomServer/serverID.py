import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path

from plom import specdir

log = logging.getLogger("servID")


def IDprogressCount(self):
    """Send back current ID progress counts to the client"""
    return [self.DB.IDcountIdentified(), self.DB.IDcountAll()]


def IDgetNextTask(self):
    # Get number of next unidentified test from the database
    give = self.DB.IDgetNextTask()
    if give is None:
        return [False]
    else:
        return [True, give]


def IDgetDoneTasks(self, user):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list.
    """
    return self.DB.IDgetDoneTasks(user)


def IDgetImage(self, username, testNumber):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list.
    """
    return self.DB.IDgetImage(username, testNumber)


def IDclaimThisTask(self, user, testNumber):
    return self.DB.IDgiveTaskToClient(user, testNumber)
    # return [true, image-filename1, name2,...]
    # or return [false]


def IDreturnIDdTask(self, user, ret, sid, sname):
    """Client has ID'd the pageimage with code=ret, student-number=sid,
    and student-name=sname. Send the information to the database (which
    checks if that number has been used previously). If okay then send
    and ACK, else send an error that the number has been used.
    """
    # TODO - improve this
    # returns [True] if all good
    # [False, True] - if student number already in use
    # [False, False] - if bigger error
    return self.DB.IDtakeTaskFromClient(ret, user, sid, sname)


def IDdidNotFinish(self, user, testNumber):
    """User didn't finish IDing the image with given code. Tell the
    database to put this back on the todo-pile.
    """
    self.DB.IDdidNotFinish(user, testNumber)
    return


def IDgetRandomImage(self):
    return self.DB.IDgetRandomImage()


def IDdeletePredictions(self):
    # move old file out of way
    if not os.path.isfile(Path(specdir) / "predictionlist.csv"):
        return False
    shutil.move(
        Path(specdir) / "predictionlist.csv", Path(specdir) / "predictionlist.bak"
    )
    with open(Path(specdir) / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
    log.info("ID prediction list deleted")

    return True


def IDreviewID(self, testNumber):
    return self.DB.IDreviewID(testNumber)


def IDrunPredictions(self, rectangle, fileNumber, ignoreStamp):
    # from plom.server.IDReader.idReader import runIDReader

    lockFile = os.path.join(specdir, "IDReader.lock")
    timestamp = os.path.join(specdir, "IDReader.timestamp")
    if os.path.isfile(lockFile):
        log.info("ID reader is already running.")
        return [True, False]

    from datetime import datetime
    import json
    import subprocess

    # check the timestamp - unless manager tells you to ignore it.
    if os.path.isfile(timestamp):
        if ignoreStamp is False:
            with open(timestamp, "r") as fh:
                txt = json.load(fh)
                return [False, txt]
        else:
            os.unlink(timestamp)

    # get list of [testNumber, image]
    log.info("ID get images for ID reader")
    testImageDict = self.DB.IDgetImageList(fileNumber)
    # dump this as json / lockfile for subprocess to use in background.
    with open(lockFile, "w") as fh:
        json.dump([testImageDict, rectangle], fh)
    # make a timestamp
    runAt = datetime.now().strftime("%y:%m:%d-%H:%M:%S")
    with open(timestamp, "w") as fh:
        json.dump(runAt, fh)

    # run the reader

    log.info("ID launch ID reader in background")
    subprocess.Popen(["python3", "-m", "plom.server.IDReader.runTheReader", lockFile])
    return [True, True]
