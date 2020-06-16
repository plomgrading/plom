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


def id_paper(self, *args, **kwargs):
    """Some glue between service routes and the database.

    See :func:`plom.db.db_identify.id_paper` for details.
    """
    return self.DB.id_paper(*args, **kwargs)


def IDdidNotFinish(self, user, testNumber):
    """User didn't finish IDing the image with given code. Tell the
    database to put this back on the todo-pile.
    """
    self.DB.IDdidNotFinish(user, testNumber)
    return


def IDgetImageFromATest(self):
    return self.DB.IDgetImageFromATest()


def IDdeletePredictions(self):
    # check to see if predictor is running
    lockFile = os.path.join(specdir, "IDReader.lock")
    if os.path.isfile(lockFile):
        log.info("ID reader currently running.")
        return [False, "ID reader is currently running"]

    # move old file out of way
    if not os.path.isfile(Path(specdir) / "predictionlist.csv"):
        return [False, "No prediction file present."]
    shutil.move(
        Path(specdir) / "predictionlist.csv", Path(specdir) / "predictionlist.bak"
    )
    with open(Path(specdir) / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
    log.info("ID prediction list deleted")

    return [True]


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
    testImageDict = self.DB.IDgetImageByNumber(fileNumber)
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
