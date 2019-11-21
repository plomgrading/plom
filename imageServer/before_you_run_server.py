__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import asyncio
import datetime
import errno
import glob
import imghdr
import json
import logging
import os
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile

from id_storage import *
from mark_storage import *
from total_storage import *
from authenticate import Authority

sys.path.append("..")  # this allows us to import from ../resources
from resources.testspecification import TestSpecification
from resources.version import __version__
from resources.version import Plom_API_Version as serverAPI

# Set up loggers for server, marking and ID-ing
def setupLogger(name, log_file, level=logging.INFO):
    # For setting up separate logging for IDing and Marking
    # https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
    """Function setup as many loggers as you want"""
    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%x %X")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


SLogger = setupLogger("SLogger", "server.log")
IDLogger = setupLogger("IDLogger", "identity_storage.log")
MarkLogger = setupLogger("MarkLogger", "mark_storage.log")
TotalLogger = setupLogger("TotalLogger", "total_storage.log")

# # # # # # # # # # # #
# These functions need improving - read from the JSON files?
def readExamsGrouped():
    """Read the list of exams that were grouped after scanning.
    Store in examsGrouped.
    """
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open("../resources/examsGrouped.json") as data_file:
            examsGrouped = json.load(data_file)


def readExamsProduced():
    """Read the list of exams that were grouped after scanning.
    Store in examsGrouped.
    """
    global examsProduced
    if os.path.exists("../resources/examsProduced.json"):
        with open("../resources/examsProduced.json") as data_file:
            examsProduced = json.load(data_file)


def findPageGroups():
    """Read the filenames of all the groups produced after scanning.
    Store in pageGroupsForGrading by tgv code.
    """
    global pageGroupsForGrading
    for pg in range(1, spec.getNumberOfGroups() + 1):
        for fname in glob.glob(
            "{}/group_{}/*/*.png".format(pathScanDirectory, str(pg).zfill(2))
        ):
            print("Adding pageimage from {}".format(fname))
            # Since file is tXXXXgYYvZ.png - get the tgv by deleting 4 char.
            pageGroupsForGrading[os.path.basename(fname)[:-4]] = fname


# # # # # # # # # # # #


class PreServer(object):
    def __init__(self, id_db, mark_db, total_db, tspec, logger):
        """Init the server, grab the ID and Mark databases, and the test-spec
        """
        self.IDDB = id_db
        self.MDB = mark_db
        self.TDB = total_db
        self.testSpec = tspec
        self.logger = logger

    def populateDatabases(self):
        """Load the IDgroup page images for identifying
        and the group-images for marking.
        The ID-images are stored in the IDDB, and the
        image for marking in the MDB.
        """
        self.logger.info("Populating databases.")
        # Load in the idgroup images and the pagegroup images
        self.logger.info("Adding IDgroups {}".format(sorted(examsGrouped.keys())))
        for t in sorted(examsGrouped.keys()):
            if (
                t in examsProduced
                and "id" in examsProduced[t]
                and "name" in examsProduced[t]
            ):
                self.logger.info(
                    "Adding id group {} with ID {} and name {}".format(
                        examsGrouped[t][0],
                        examsProduced[t]["id"],
                        examsProduced[t]["name"],
                    )
                )
                self.IDDB.addPreIDdExam(
                    int(t),
                    "t{:s}idg".format(t.zfill(4)),
                    examsProduced[t]["id"],
                    examsProduced[t]["name"],
                )
            else:
                self.IDDB.addUnIDdExam(int(t), "t{:s}idg".format(t.zfill(4)))

        self.logger.info("Adding Total-images {}".format(sorted(examsGrouped.keys())))
        for t in sorted(examsGrouped.keys()):
            self.TDB.addUntotaledExam(int(t), "t{:s}idg".format(t.zfill(4)))

        self.logger.info("Adding TGVs {}".format(sorted(pageGroupsForGrading.keys())))
        for tgv in sorted(pageGroupsForGrading.keys()):
            # tgv is t1234g67v9
            t, pg, v = int(tgv[1:5]), int(tgv[6:8]), int(tgv[9])
            self.MDB.addUnmarkedGroupImage(t, pg, v, tgv, pageGroupsForGrading[tgv])


def checkDirectories():
    if not os.path.isdir("markedPapers"):
        os.mkdir("markedPapers")
    if not os.path.isdir("markedPapers/plomFiles"):
        os.mkdir("markedPapers/plomFiles")
    if not os.path.isdir("markedPapers/commentFiles"):
        os.mkdir("markedPapers/commentFiles")


print("Plom Server v{}: this is free software without warranty".format(__version__))
# check that markedPapers and subdirectories exist
checkDirectories()

# Read the test specification
spec = TestSpecification()
spec.readSpec()
# Read in the exams that have been grouped after
# scanning and the filenames of the group-images
# that need marking.
examsGrouped = {}
examsProduced = {}
pageGroupsForGrading = {}
readExamsGrouped()
readExamsProduced()
findPageGroups()

# Set up the classes for handling transactions with databases
# Pass them the loggers
theIDDB = IDDatabase(IDLogger)
theMarkDB = MarkDatabase(MarkLogger)
theTotalDB = TotalDatabase(TotalLogger)
# Fire up the server with both database client classes and the test-spec.
peon = PreServer(theIDDB, theMarkDB, theTotalDB, spec, SLogger)
peon.populateDatabases()

# close the rest of the stuff
SLogger.info("Closing databases")
print("Closing databases")
theIDDB.saveIdentified()
theMarkDB.saveMarked()
theTotalDB.saveTotaled()
