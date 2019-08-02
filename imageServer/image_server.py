__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import asyncio
import datetime
import errno
import glob
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

__version__ = "0.1.0+"

# default server values and location of grouped-scans.
serverInfo = {"server": "127.0.0.1", "mport": 41984, "wport": 41985}
pathScanDirectory = "../scanAndGroup/readyForMarking/"
# # # # # # # # # # # #
# Fire up ssl for network communications
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
sslContext.load_cert_chain("../resources/mlp-selfsigned.crt", "../resources/mlp.key")


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
            for n in examsGrouped.keys():
                print("Adding id group {}".format(examsGrouped[n][0]))


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


def getServerInfo():
    """Read the server info from json."""
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open("../resources/serverDetails.json") as data_file:
            serverInfo = json.load(data_file)
            print("Server details loaded: ", serverInfo)
    else:
        print("Cannot find server details.")


# # # # # # # # # # # #
# A dict of messages from client and corresponding server commands.
servCmd = {
    "AUTH": "authoriseUser",
    "UCL": "userClosing",
    "iDNF": "IDdidntFinish",
    "iNID": "IDnextUnIDd",
    "iPRC": "IDprogressCount",
    "iRID": "IDreturnIDd",
    "iRAD": "IDreturnAlreadyIDd",
    "iRCL": "IDrequestClassList",
    "iRPL": "IDrequestPredictionList",
    "iGAL": "IDgetAlreadyIDList",
    "iGGI": "IDgetGroupImage",
    "iDWF": "IDdoneWithFile",
    "mDNF": "MdidntFinish",
    "mNUM": "MnextUnmarked",
    "mPRC": "MprogressCount",
    "mUSO": "MuserStillOwns",
    "mRMD": "MreturnMarked",
    "mGMX": "MgetPageGroupMax",
    "mGML": "MgetMarkedPaperList",
    "mGGI": "MgetGroupImages",
    "mDWF": "MdoneWithFile",
    "mGWP": "MgetWholePaper",
    "mLTT": "MlatexThisText",
    "mRCF": "MreturnCommentFile",
    "mRPF": "MreturnPlomFile",
    "mTAG": "MsetTag",
    "tGMM": "TgetMaxMark",
    "tGTP": "TgotTest",
    "tPRC": "TprogressCount",
    "tNUT": "TnextUntotaled",
    "tDNF": "TdidntFinish",
    "tRAT": "TreturnAlreadyTotaled",
    "tRUT": "TreturnTotaled",
    "tGAT": "TgetAlreadyTotaledList",
    "tDWF": "TdoneWithFile",
    "tGGI": "TgetGroupImage",
}


async def handle_messaging(reader, writer):
    """Asyncio messager handler.
    Reads message from the stream.
    Message should be a list [cmd, user, password, arg1, arg2, etc]
    Converts message[0] to the server command using the servCmd dictionary
    Server, peon, then runs command and we send back the return message.
    """
    data = await reader.read(1024)
    terminate = data.endswith(b"\x00")
    data = data.rstrip(b"\x00")
    message = json.loads(data.decode())
    # print("Got message {}".format(message))

    # message should be a list [cmd, user, password, arg1, arg2, etc]
    if not isinstance(message, list):
        SLogger.info(">>> Got strange message - not a list. {}".format(message))
    else:
        if message[0] == "AUTH":
            # do not log the password - just auth and username
            SLogger.info("Got auth request: {}".format(message[:2]))
        else:
            SLogger.info("Got message: {}".format(message))
        # Run the command on the server and get the return message.
        # peon will be the instance of the server when it runs.
        rmesg = peon.proc_cmd(message)
        SLogger.info("Returning message {}".format(rmesg))

    addr = writer.get_extra_info("peername")
    # convert message to json
    jdm = json.dumps(rmesg)
    # send encoded-json'd message back over connection.
    writer.write(jdm.encode())
    # SSL does not support EOF, so send a null byte
    # to indicate the end of the message.
    writer.write(b"\x00")
    await writer.drain()
    writer.close()


# # # # # # # # # # # #


class Server(object):
    def __init__(self, id_db, mark_db, total_db, tspec, logger):
        """Init the server, grab the ID and Mark databases, and the test-spec
        """
        self.IDDB = id_db
        self.MDB = mark_db
        self.TDB = total_db
        self.testSpec = tspec
        self.logger = logger
        self.logger.info("Loading images and users.")
        # Load in the idgroup images and the pagegroup images
        self.loadPapers()
        # Load in the list of users who will run the client app.
        self.loadUsers()

    def loadUsers(self):
        """Load the users from json file, add them to the authority which
        handles authentication for us.
        """
        self.logger.info("Loading user list")
        # Look for the file.
        if os.path.exists("../resources/userList.json"):
            with open("../resources/userList.json") as data_file:
                # Load the users and pass them to the authority.
                self.userList = json.load(data_file)
                self.authority = Authority(self.userList)
                self.logger.info("Users = {}".format(list(self.userList.keys())))
        else:
            # Cannot find users - give error and quit out.
            self.logger.info(">>> Cannot find user/password file.")
            print("Where is user/password file?")
            quit()

    def reloadImages(self, password):
        """Reload all the grouped exams and all the page images.
        """
        # Check user is manager.
        if not self.authority.authoriseUser("Manager", password):
            return ["ERR", "You are not authorised to reload images"]
        self.logger.info("Reloading group images")
        # Read in the groups and images again.
        readExamsGrouped()
        findPageGroups()
        self.loadPapers()
        # Send acknowledgement back to manager.
        return ["ACK"]

    def reloadUsers(self, password):
        """Reload the user list."""
        # Check user is manager.
        if not self.authority.authoriseUser("Manager", password):
            return ["ERR", "You are not authorised to reload users"]
        self.logger.info("Reloading the user list")
        # Load in the user list and check against existing user list for differences
        if os.path.exists("../resources/userList.json"):
            with open("../resources/userList.json") as data_file:
                newUserList = json.load(data_file)
                # for each user in the new list..
                for u in newUserList:
                    if u not in self.userList:
                        # This is a new user - add them in.
                        self.userList[u] = newUserList[u]
                        self.authority.addUser(u, newUserList[u])
                        self.logger.info("New user = {}".format(u))
                # for each user in the old list..
                for u in self.userList:
                    if u not in newUserList:
                        # this user has been removed
                        self.logger.info("Removing user = {}".format(u))
                        # Anything out at user should go back on todo pile.
                        self.IDDB.resetUsersToDo(u)
                        self.MDB.resetUsersToDo(u)
                        # remove user's authorisation token.
                        self.authority.detoken(u)
        self.logger.info("Current user list = {}".format(list(self.userList.keys())))
        # return acknowledgement to manager.
        return ["ACK"]

    def proc_cmd(self, message):
        """Process the server command in the message
        Message should be a list [cmd, user, password, arg1, arg2, etc]
        Basic comands are handled in this function.
        More complicated ones are run as separate functions.
        """
        # convert the command in message[0] to a function-call
        # if cannot convert then exec msgError()
        pcmd = servCmd.get(message[0], "msgError")
        if message[0] == "PING":
            # Client has sent a ping to test if server is up
            # so we return an ACK
            return ["ACK"]
        elif message[0] == "AUTH":
            # Client is requesting authentication
            # message should be ['AUTH', user, password]
            # So we return their authentication token (if they are legit)
            return self.authoriseUser(*message[1:])
        elif message[0] == "RUSR":
            # Manager is requesting server reload users.
            # message should be ['RUSR', managerpwd]
            rv = self.reloadUsers(*message[1:])
            return rv
        elif message[0] == "RIMR":
            # Manager is requesting server reload images
            # message should be ['RIMR', managerpwd]
            rv = self.reloadImages(*message[1:])
            return rv
        else:
            # Otherwise client is making a normal request
            # should be ['CMD', user, token, arg1, arg2,...]
            # first check if user is authorised - check their authorisation token.
            if self.validate(message[1], message[2]):
                # user is authorised, so run their requested function
                return getattr(self, pcmd)(*message[1:])
            else:
                self.logger.info(">>> Unauthorised attempt by user {}".format(user))
                print("Attempt by non-user to {}".format(message))
                return ["ERR", "You are not an authorised user"]

    def authoriseUser(self, user, password):
        """When a user requests authorisation
        They have sent their name and password
        first check if they are a valid user
        if so then anything that is recorded as out with that user
        should be reset as todo.
        Then pass them back the authorisation token
        (the password is only checked on first authorisation - since slow)
        """
        if self.authority.authoriseUser(user, password):
            # On token request also make sure anything "out" with that user is reset as todo.
            self.IDDB.resetUsersToDo(user)
            self.MDB.resetUsersToDo(user)
            self.TDB.resetUsersToDo(user)
            self.logger.info("Authorising user {}".format(user))
            return ["ACK", self.authority.getToken(user)]
        else:
            return ["ERR", "You are not an authorised user"]

    def validate(self, user, token):
        """Check the user's token is valid"""
        return self.authority.validateToken(user, token)

    def loadPapers(self):
        """Load the IDgroup page images for identifying
        and the group-images for marking.
        The ID-images are stored in the IDDB, and the
        image for marking in the MDB.
        """
        self.logger.info("Adding IDgroups {}".format(sorted(examsGrouped.keys())))
        for t in sorted(examsGrouped.keys()):
            self.IDDB.addUnIDdExam(int(t), "t{:s}idg".format(t.zfill(4)))

        self.logger.info("Adding Total-images {}".format(sorted(examsGrouped.keys())))
        for t in sorted(examsGrouped.keys()):
            self.TDB.addUntotaledExam(int(t), "t{:s}idg".format(t.zfill(4)))

        self.logger.info("Adding TGVs {}".format(sorted(pageGroupsForGrading.keys())))
        for tgv in sorted(pageGroupsForGrading.keys()):
            # tgv is t1234g67v9
            t, pg, v = int(tgv[1:5]), int(tgv[6:8]), int(tgv[9])
            self.MDB.addUnmarkedGroupImage(t, pg, v, tgv, pageGroupsForGrading[tgv])

    def provideFile(self, fname):
        """Copy a file (temporarily) into the webdav for a client,
        and return the temp-filename to the client.
        """
        tfn = tempfile.NamedTemporaryFile(delete=False, dir=davDirectory)
        shutil.copy(fname, tfn.name)
        return os.path.basename(tfn.name)

    def claimFile(self, fname, subdir):
        """Once an image has been marked, the server copies the image
        back from the webdav and into markedPapers or appropriate
        subdirectory.
        """
        srcfile = os.path.join(davDirectory, fname)
        dstfile = os.path.join("markedPapers", subdir, fname)
        # Check if file already exists
        if os.path.isfile(dstfile):
            # backup the older file with a timestamp
            os.rename(
                dstfile,
                dstfile + ".regraded_at_" + datetime.now().strftime("%d_%H-%M-%S"),
            )
        # This should really use path-join.
        shutil.move(srcfile, dstfile)
        # Copy with full name (not just directory) so can overwrite properly - else error on overwrite.

    def removeFile(self, davfn):
        """Once a file has been grabbed by the client, delete it from the webdav.
        """
        os.unlink(davDirectory + "/" + davfn)

    def printToDo(self):
        """Ask each database to print the images that are still on
        the todo pile
        """
        self.IDDB.printToDo()
        self.MDB.printToDo()

    def printOutForMarking(self):
        """Ask the database to print the images that are currently
        out for marking
        """
        self.MDB.printOutForMarking()

    def printOutForIDing(self):
        """Ask the database to print the images that are currently
        out for identifying.
        """
        self.IDDB.printOutForIDing()

    def printMarked(self):
        """Ask the database to print the images that have been marked.
        """
        self.MDB.printIdentified()

    def printIdentified(self):
        """Ask the database to print the images that have been identified.
        """
        self.IDDB.printIdentified()

    def msgError(self, *args):
        """The client sent a strange message, so send back an error message.
        """
        return ["ERR", "Some sort of command error - what did you send?"]

    def IDrequestClassList(self, user, token):
        """The client requests the classlist, so the server copies
        the class list to the webdav and returns the temp webdav path
        to that file to the client.
        """
        return ["ACK", self.provideFile("../resources/classlist.csv")]

    def IDrequestPredictionList(self, user, token):
        return ["ACK", self.provideFile("../resources/predictionlist.csv")]

    def IDdoneWithFile(self, user, token, tfn):
        """The client acknowledges they got the file,
        so the server deletes it and sends back an ACK.
        """
        self.removeFile(tfn)
        return ["ACK"]

    def MgetPageGroupMax(self, user, token, pg, v):
        """When a marked-client logs on they need the max mark for the group
        they are marking. Check the (group/version) is valid and then send back
        the corresponding mark from the test spec.
        """
        iv = int(v)
        ipg = int(pg)
        if ipg < 1 or ipg > self.testSpec.getNumberOfGroups():
            return ["ERR", "Pagegroup out of range"]
        if iv < 1 or iv > self.testSpec.Versions:
            return ["ERR", "Version out of range"]
        # Send an ack with the max-mark for the pagegroup.
        return ["ACK", self.testSpec.Marks[ipg]]

    def IDdidntFinish(self, user, token, code):
        """User didn't finish IDing the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.IDDB.didntFinish(user, code)
        # send back an ACK.
        return ["ACK"]

    def MdidntFinish(self, user, token, tgv):
        """User didn't finish marking the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.MDB.didntFinish(user, tgv)
        # send back an ACK.
        return ["ACK"]

    def TdidntFinish(self, user, token, code):
        """User didn't finish totaling the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.TDB.didntFinish(user, code)
        # send back an ACK.
        return ["ACK"]

    def userClosing(self, user, token):
        """Client is closing down their app, so remove the authorisation token
        """
        self.authority.detoken(user)
        return ["ACK"]

    def IDnextUnIDd(self, user, token):
        """The client has asked for the next unidentified paper, so
        ask the database for its code and then copy the appropriate file
        into the webdav and send code and the temp-webdav path back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.IDDB.giveIDImageToClient(user)
        if give is None:
            return ["ERR", "No more papers"]
        else:
            # copy the file into the webdav and tell client the code and path
            return [
                "ACK",
                give,
                self.provideFile("{}/idgroup/{}.png".format(pathScanDirectory, give)),
            ]

    def IDprogressCount(self, user, token):
        """Send back current ID progress counts to the client"""
        return ["ACK", self.IDDB.countIdentified(), self.IDDB.countAll()]

    def IDreturnIDd(self, user, token, ret, sid, sname):
        """Client has ID'd the pageimage with code=ret, student-number=sid,
        and student-name=sname. Send the information to the database (which
        checks if that number has been used previously). If okay then send
        and ACK, else send an error that the number has been used.
        """
        if self.IDDB.takeIDImageFromClient(ret, user, sid, sname):
            return ["ACK"]
        else:
            return ["ERR", "That student number already used."]

    def IDreturnAlreadyIDd(self, user, token, ret, sid, sname):
        """Client has re-ID'd the pageimage with code=ret, student-number=sid,
        and student-name=sname. Send the information to the database (which
        checks if that number has been used previously). If okay then send
        and ACK, else send an error that the number has been used.
        """
        self.IDDB.takeIDImageFromClient(ret, user, sid, sname)
        return ["ACK"]

    def IDgetAlreadyIDList(self, user, token):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back a textfile with list of TGVs.
        """
        idList = self.IDDB.buildIDList(user)
        # dump the list to file as json and then give file to client
        tfn = tempfile.NamedTemporaryFile()
        with open(tfn.name, "w") as outfile:
            json.dump(idList, outfile)
        # Send an ack with the file
        return ["ACK", self.provideFile(tfn.name)]

    def IDgetGroupImage(self, user, token, tgv):
        give = self.IDDB.getGroupImage(user, tgv)
        fname = "{}/idgroup/{}.png".format(pathScanDirectory, give)
        if fname is not None:
            return ["ACK", give, self.provideFile(fname), None]
        else:
            return ["ERR", "User {} is not authorised for tgv={}".format(user, tgv)]

    def MnextUnmarked(self, user, token, pg, v):
        """The client has asked for the next unmarked image (with
        group pg, and version v), so ask the database for its code and
        then copy the appropriate file into the webdav and send code
        and the temp-webdav path back to the client.
        """
        give, fname, tag = self.MDB.giveGroupImageToClient(user, pg, v)
        if give is None:
            return ["ERR", "Nothing left on todo pile"]
        else:
            # copy the file into the webdav and tell client code / path.
            return ["ACK", give, self.provideFile(fname), tag]

    def MprogressCount(self, user, token, pg, v):
        """Send back current marking progress counts to the client"""
        return ["ACK", self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

    def MdoneWithFile(self, user, token, filename):
        """Client acknowledges they got the file, so
        server deletes it from the webdav and sends an ack.
        """
        self.removeFile(filename)
        return ["ACK"]

    def MuserStillOwns(self, user, token, code):
        """Check that user still 'owns' the tgv = code"""
        if self.MDB.userStillOwnsTGV(code, user):
            return ["ACK"]
        else:
            return ["ERR", "You are no longer authorised to upload that tgv"]

    def MreturnMarked(
        self, user, token, code, mark, fname, pname, cname, mtime, pg, v, tags
    ):
        """Client has marked the pageimage with code, mark, annotated-file-name
        (which the client has uploaded to webdav), and spent mtime marking it.
        Send the information to the database and send an ack.
        """
        # move annoted file to right place with new filename
        self.MDB.takeGroupImageFromClient(
            code, user, mark, fname, pname, cname, mtime, tags
        )
        self.recordMark(user, mark, fname, mtime, tags)
        self.claimFile(fname, "")
        self.claimFile(pname, "plomFiles")
        self.claimFile(cname, "commentFiles")
        # return ack with current counts.
        return ["ACK", self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

    def recordMark(self, user, mark, fname, mtime, tags):
        """For test blah.png, we record, in blah.png.txt, as a backup
        the filename, mark, user, time, marking time and any tags.
        This is not used.
        """
        fh = open("./markedPapers/{}.txt".format(fname), "w")
        fh.write(
            "{}\t{}\t{}\t{}\t{}\t{}".format(
                fname,
                mark,
                user,
                datetime.now().strftime("%Y-%m-%d,%H:%M"),
                mtime,
                tags,
            )
        )
        fh.close()

    def MgetMarkedPaperList(self, user, token, pg, v):
        """When a marked-client logs on they request a list of papers they have already marked.
        Check the (group/version) is valid and then send back a textfile with list of TGVs.
        """
        iv = int(v)
        ipg = int(pg)
        if ipg < 1 or ipg > self.testSpec.getNumberOfGroups():
            return ["ERR", "Pagegroup out of range"]
        if iv < 1 or iv > self.testSpec.Versions:
            return ["ERR", "Version out of range"]
        markedList = self.MDB.buildMarkedList(user, pg, v)
        # dump the list to file as json and then give file to client
        tfn = tempfile.NamedTemporaryFile()
        with open(tfn.name, "w") as outfile:
            json.dump(markedList, outfile)
        # Send an ack with the file
        return ["ACK", self.provideFile(tfn.name)]

    def MgetGroupImages(self, user, token, tgv):
        give, fname, aname = self.MDB.getGroupImage(user, tgv)
        if fname is not None:
            if aname is not None:
                # plom file is same as annotated file just with suffix plom
                return [
                    "ACK",
                    give,
                    self.provideFile(fname),
                    self.provideFile("markedPapers/" + aname),
                    self.provideFile("markedPapers/plomFiles/" + aname[:-3] + "plom"),
                ]
            else:
                return ["ACK", give, self.provideFile(fname), None]
        else:
            return ["ERR", "Non-existant tgv={}".format(tgv)]

    def MsetTag(self, user, token, tgv, tag):
        if self.MDB.setTag(user, tgv, tag):
            return ["ACK"]
        else:
            return ["ERR", "Non-existant tgv={}".format(tgv)]

    def MgetWholePaper(self, user, token, testNumber):
        # client passes the tgv code of their current group image.
        # from this we infer the test number.
        files = self.MDB.getTestAll(testNumber)
        msg = ["ACK"]
        for f in files:
            msg.append(self.provideFile(f))
        return msg

    def MlatexThisText(self, user, token, fragmentFile):
        fragment = os.path.join(davDirectory, fragmentFile)
        tfn = tempfile.NamedTemporaryFile()
        if (
            subprocess.run(["python3", "latex2png.py", fragment, tfn.name]).returncode
            == 0
        ):
            msg = ["ACK", True, self.provideFile(tfn.name)]
        else:
            msg = ["ACK", False]
        return msg

    def TgetMaxMark(self, user, token):
        return ["ACK", sum(spec.Marks)]

    def TgotTest(self, user, token, test, tfn):
        """Client acknowledges they got the test pageimage, so server
        deletes it from the webdav and sends an ack.
        """
        self.removeFile(tfn)
        return ["ACK"]

    def TprogressCount(self, user, token):
        """Send back current total progress counts to the client"""
        return ["ACK", self.TDB.countTotaled(), self.TDB.countAll()]

    def TnextUntotaled(self, user, token):
        """The client has asked for the next untotaled paper, so
        ask the database for its code and then copy the appropriate file
        into the webdav and send code and the temp-webdav path back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.TDB.giveTotalImageToClient(user)
        if give is None:
            return ["ERR", "No more papers"]
        else:
            # copy the file into the webdav and tell client the code and path
            return [
                "ACK",
                give,
                self.provideFile("{}/idgroup/{}.png".format(pathScanDirectory, give)),
            ]

    def TreturnTotaled(self, user, token, ret, value):
        """Client has totaled the pageimage with code=ret, total=value.
        Send the information to the database and return an ACK
        """
        self.TDB.takeTotalImageFromClient(ret, user, value)
        return ["ACK"]

    def TreturnAlreadyTotaled(self, user, token, ret, value):
        """ As per TReturnTotaled"""
        self.TDB.takeTotalImageFromClient(ret, user, value)
        return ["ACK"]

    def TgetAlreadyTotaledList(self, user, token):
        """When a total-client logs on they request a list of papers they have already totaled.
        Send back a textfile with list of TGVs.
        """
        tList = self.TDB.buildTotalList(user)
        # dump the list to file as json and then give file to client
        tfn = tempfile.NamedTemporaryFile()
        with open(tfn.name, "w") as outfile:
            json.dump(tList, outfile)
        # Send an ack with the file
        return ["ACK", self.provideFile(tfn.name)]

    def TdoneWithFile(self, user, token, tfn):
        """The client acknowledges they got the file,
        so the server deletes it and sends back an ACK.
        """
        self.removeFile(tfn)
        return ["ACK"]

    def TgetGroupImage(self, user, token, tgv):
        give = self.TDB.getGroupImage(user, tgv)
        fname = "{}/idgroup/{}.png".format(pathScanDirectory, give)
        if fname is not None:
            return ["ACK", give, self.provideFile(fname), None]
        else:
            return ["ERR", "User {} is not authorised for tgv={}".format(user, tgv)]


# # # # # # # # # # # #
# # # # # # # # # # # #


def checkPortFree(ip, port):
    """Test if the given port is free so server can use it
    for messaging and/or webdav.
    """
    # Create a socket.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # try to bind it to the IP and port.
    try:
        sock.bind((ip, port))
    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            return False
        else:
            SLogger.info(
                "There is some sort of ip/port error. Number = {}".format(err.errno)
            )
            print("There is some sort of ip/port error. Number = {}".format(err.errno))
            return False
    return True


def checkPorts():
    """Check that the messaging and webdav ports are free
    on the server.
    """
    if checkPortFree(serverInfo["server"], serverInfo["mport"]):
        SLogger.info("Messaging port is free and working.")
        print("Messaging port is free and working.")
    else:
        SLogger.info(
            "Problem with messaging port {} on server {}. "
            "Please check and try again.".format(
                serverInfo["mport"], serverInfo["server"]
            )
        )
        print(
            "Problem with messaging port {} on server {}. "
            "Please check and try again.".format(
                serverInfo["mport"], serverInfo["server"]
            )
        )
        exit()

    if checkPortFree(serverInfo["server"], serverInfo["wport"]):
        SLogger.info("Webdav port is free and working.")
        print("Webdav port is free and working.")
    else:
        SLogger.info(
            "Problem with webdav port {} on server {}. "
            "Please check and try again.".format(
                serverInfo["wport"], serverInfo["server"]
            )
        )
        print(
            "Problem with webdav port {} on server {}. "
            "Please check and try again.".format(
                serverInfo["wport"], serverInfo["server"]
            )
        )
        exit()


def checkDirectories():
    if not os.path.isdir("markedPapers"):
        os.mkdir("markedPapers")
    if not os.path.isdir("markedPapers/plomFiles"):
        os.mkdir("markedPapers/plomFiles")
    if not os.path.isdir("markedPapers/commentFiles"):
        os.mkdir("markedPapers/commentFiles")


print("PLOM v{0}: image server starting...".format(__version__))
# Get the server information from file
getServerInfo()
# Check the server ports are free
checkPorts()
# check that markedPapers and subdirectories exist
checkDirectories()

# Create a temp directory for the webdav
tempDirectory = tempfile.TemporaryDirectory()
davDirectory = tempDirectory.name
# Give directory correct permissions.
os.system("chmod o-r {}".format(davDirectory))
SLogger.info("Webdav directory = {}".format(davDirectory))
# Fire up the webdav server.
cmd = "wsgidav -q -H {} -p {} --server cheroot -r {} -c ../resources/davconf.yaml".format(
    serverInfo["server"], serverInfo["wport"], davDirectory
)
davproc = subprocess.Popen(shlex.split(cmd))

# Read the test specification
spec = TestSpecification()
spec.readSpec()
# Read in the exams that have been grouped after
# scanning and the filenames of the group-images
# that need marking.
examsGrouped = {}
pageGroupsForGrading = {}
readExamsGrouped()
findPageGroups()

# Set up the classes for handling transactions with databases
# Pass them the loggers
theIDDB = IDDatabase(IDLogger)
theMarkDB = MarkDatabase(MarkLogger)
theTotalDB = TotalDatabase(TotalLogger)
# Fire up the server with both database client classes and the test-spec.
peon = Server(theIDDB, theMarkDB, theTotalDB, spec, SLogger)

# # # # # # # # # # # #
# Fire up the asyncio event loop.
loop = asyncio.get_event_loop()
coro = asyncio.start_server(
    handle_messaging,
    serverInfo["server"],
    serverInfo["mport"],
    loop=loop,
    ssl=sslContext,
)
try:
    server = loop.run_until_complete(coro)
except OSError:
    SLogger.info(
        "There is a problem running the socket-listening loop. "
        "Check if port {} is free and try again.".format(serverInfo["mport"])
    )
    print(
        "There is a problem running the socket-listening loop. "
        "Check if port {} is free and try again.".format(serverInfo["mport"])
    )
    subprocess.Popen.kill(davproc)
    loop.close()
    exit()

SLogger.info("Serving messages on {}".format(server.sockets[0].getsockname()))
print("Serving messages on {}".format(server.sockets[0].getsockname()))
try:
    # Run the event loop until it is killed off.
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close down the event loop.
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()

# # # # # # # # # # # #
# Close the webdav server
subprocess.Popen.kill(davproc)
SLogger.info("Webdav server closed")
print("Webdav server closed")
SLogger.info("Closing databases")
print("Closing databases")
theIDDB.saveIdentified()
theMarkDB.saveMarked()
theTotalDB.saveTotaled()
