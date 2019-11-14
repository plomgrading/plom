__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from aiohttp import web, MultipartWriter
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

# default server values and location of grouped-scans.
serverInfo = {"server": "127.0.0.1", "mport": 41984, "wport": 41985}
pathScanDirectory = "../scanAndGroup/readyForMarking/"
# # # # # # # # # # # #
# Fire up ssl for network communications
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
sslContext.load_cert_chain("../resources/mlp-selfsigned.crt", "../resources/mlp.key")

# ----------------------
# ----------------------

# aiohttp-ificiation of things
routes = web.RouteTableDef()


@routes.put("/")
async def hello(request):
    data = await request.json()
    message = data["msg"]
    print("Got message {}".format(message))

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
        print("Returning message {}".format(rmesg))
        SLogger.info("Returning message {}".format(rmesg))
        return web.json_response({"rmsg": rmesg}, status=200)


# ----------------------
# ----------------------
# Authentication / closing stuff


@routes.get("/Version")
async def Version(request):
    return web.Response(
        text="Running Plom server version {} with API {}".format(
            __version__, serverAPI
        ),
        status=200,
    )


@routes.delete("/users/{user}")
async def CloseUser(request):
    data = await request.json()
    user = request.match_info["user"]
    if data["user"] != request.match_info["user"]:
        return web.Response(status=400)  # malformed request.
    elif peon.validate(data["user"], data["token"]):
        peon.userClosing(data["user"])
        return web.Response(status=200)
    else:
        return web.Response(status=401)


@routes.put("/users/{user}")
async def LoginUserGiveToken(request):
    data = await request.json()
    user = request.match_info["user"]

    rmsg = peon.authoriseUser(data["user"], data["pw"], data["api"])
    if rmsg[0]:
        return web.json_response(rmsg[1], status=200)  # all good, return the token
    elif rmsg[1].startswith("API"):
        return web.json_response(
            rmsg[1], status=400
        )  # api error - return the error message
    else:
        return web.Response(status=401)  # you are not authorised


# ----------------------
# ----------------------
# Identifier stuff


@routes.get("/ID/progress")
async def IDprogressCount(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        return web.json_response(peon.IDprogressCount(), status=200)
    else:
        return web.Response(status=401)


@routes.get("/ID/tasks/available")
async def IDnextTask(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.IDaskNextTask(data["user"])  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left
    else:
        return web.Response(status=401)


@routes.get("/ID/classlist")
async def IDgimmetheclasslist(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        if os.path.isfile("../resources/classlist.csv"):
            return web.FileResponse("../resources/classlist.csv", status=200)
        else:
            return web.Response(status=404)
    else:
        return web.Response(status=401)


@routes.get("/ID/predictions")
async def IDgimmethepredictions(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        if os.path.isfile("../resources/predictionlist.csv"):
            return web.FileResponse("../resources/predictionlist.csv", status=200)
        else:
            return web.Response(status=404)
    else:
        return web.Response(status=401)


@routes.get("/ID/tasks/complete")
async def IDgimmewhatsdone(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(peon.IDgetAlreadyIDList(data["user"]), status=200)
    else:
        return web.Response(status=401)


@routes.get("/ID/images/{tgv}")
async def IDgetImage(request):
    data = await request.json()
    code = request.match_info["tgv"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.IDgetGroupImage(data["user"], code)
        if rmsg[0]:  # user allowed access - returns [true, fname]
            if os.path.isfile(rmsg[1]):
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=409)  # someone else has that image
    else:
        return web.Response(status=401)  # not authorised at all


# ----------------------

## ID put - do change server status.
@routes.patch("/ID/tasks/{task}")
async def IDclaimThisTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmesg = peon.IDclaimSpecificTask(data["user"], code)
        if rmesg[0]:  # return [True, filename]
            return web.FileResponse(rmesg[1], status=200)
        else:
            return web.Response(status=204)  # that task already taken.
    else:
        return web.Response(status=401)


@routes.put("/ID/tasks/{task}")
async def IDreturnIDd(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.IDreturnIDd(data["user"], code, data["sid"], data["sname"])
        # returns [True] if all good
        # [False, True] - if student number already in use
        # [False, False] - if bigger error
        if rmsg[0]:  # all good
            return web.Response(status=200)
        elif rmsg[1]:  # student number already in use
            return web.Response(status=409)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)
    else:
        return web.Response(status=401)


# ----------------------


@routes.delete("/ID/tasks/{task}")
async def IDdidNotFinishTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        peon.IDdidntFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


# ----------------------
# ----------------------
# Totaller stuff


@routes.get("/TOT/maxMark")
async def TmarkMark(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        return web.json_response(peon.TgetMaxMark(), status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/tasks/complete")
async def Tgimmewhatsdone(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(peon.TgetAlreadyTotaledList(data["user"]), status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/progress")
async def TprogressCount(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        return web.json_response(peon.TprogressCount(), status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/tasks/available")
async def TnextTask(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.TaskNextTask(data["user"])  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left
    else:
        return web.Response(status=401)


@routes.patch("/TOT/tasks/{task}")
async def TclaimThisTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmesg = peon.TclaimSpecificTask(data["user"], code)
        if rmesg[0]:  # return [True, filename]
            return web.FileResponse(rmesg[1], status=200)
        else:
            return web.Response(status=204)  # that task already taken.
    else:
        return web.Response(status=401)


@routes.delete("/TOT/tasks/{task}")
async def TdidNotFinishTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        peon.TdidntFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/images/{tgv}")
async def TgetImage(request):
    data = await request.json()
    code = request.match_info["tgv"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.TgetGroupImage(data["user"], code)
        if rmsg[0]:  # user allowed access - returns [true, fname]
            if os.path.isfile(rmsg[1]):
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=409)  # someone else has that image
    else:
        return web.Response(status=401)  # not authorised at all


@routes.put("/TOT/tasks/{task}")
async def TreturnTotaled(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.TreturnTotaled(data["user"], code, data["mark"])
        # returns True if all good, False if error
        if rmsg:  # all good
            return web.Response(status=200)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)
    else:
        return web.Response(status=401)


# ----------------------
# ----------------------
# Marker stuff


@routes.get("/MK/maxMark")
async def TmarkMark(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MgetPageGroupMax(data["pg"], data["v"])
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        elif rmsg[1] == "PGE":
            # pg out of range
            return web.Response(
                text="Page-group out of range - please check before trying again.",
                status=416,
            )
        elif rmsg[1] == "VE":
            # version our of range
            return web.Response(
                text="Version out of range - please check before trying again.",
                status=416,
            )
    else:
        return web.Response(status=401)


@routes.delete("/MK/tasks/{task}")
async def MdidNotFinishTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        peon.MdidntFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


@routes.get("/MK/tasks/complete")
async def Mgimmewhatsdone(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(
            peon.MgetMarkedList(data["user"], data["pg"], data["v"]), status=200
        )
    else:
        return web.Response(status=401)


@routes.get("/MK/progress")
async def MprogressCount(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        return web.json_response(peon.MprogressCount(data["pg"], data["v"]), status=200)
    else:
        return web.Response(status=401)


@routes.get("/MK/tasks/available")
async def MnextTask(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MaskNextTask(
            data["user"], data["pg"], data["v"]
        )  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left
    else:
        return web.Response(status=401)


@routes.patch("/MK/tasks/{task}")
async def MclaimThisTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmesg = peon.MclaimSpecificTask(data["user"], code)
        if rmesg[0]:  # return [True, filename, tags]
            with MultipartWriter("imageAndTags") as mpwriter:
                mpwriter.append(open(rmesg[1], "rb"))
                mpwriter.append_json(rmesg[2])
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=204)  # that task already taken.
    else:
        return web.Response(status=401)


@routes.get("/MK/latex")
async def MlatexFragment(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MlatexThisText(data["user"], data["fragment"])
        if rmsg[0]:  # user allowed access - returns [true, fname]
            if os.path.isfile(rmsg[1]):
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=406)  # a latex error
    else:
        return web.Response(status=401)  # not authorised at all


# ----------------------
# ----------------------

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
    #####
    "mUSO": "MuserStillOwns",
    "mRMD": "MreturnMarked",
    "mGGI": "MgetGroupImages",
    "mDWF": "MdoneWithFile",
    "mGWP": "MgetWholePaper",
    "mRCF": "MreturnCommentFile",
    "mRPF": "MreturnPlomFile",
    "mTAG": "MsetTag",
    #####
}


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
                user = message[1]
                # only exception here is if user is closing.
                # if unauth'd user tries this, just ignore.
                if message[0] == "UCL":
                    self.logger.info(
                        ">>> User {} appears to be closing out more than once.".format(
                            user
                        )
                    )
                    return ["ACK"]
                # otherwise throw an "Unauth error" to client.
                self.logger.info(">>> Unauthorised attempt by user {}".format(user))
                print("Attempt by non-user to {}".format(message))
                return ["ERR", "You are not an authorised user"]

    def authoriseUser(self, user, password, clientAPI):
        """When a user requests authorisation
        They have sent their name and password
        first check if they are a valid user
        if so then anything that is recorded as out with that user
        should be reset as todo.
        Then pass them back the authorisation token
        (the password is only checked on first authorisation - since slow)
        """
        if clientAPI != serverAPI:
            return [
                False,
                "API"
                'Plom API mismatch: client "{}" =/= server "{}". Server version is "{}"; please check you have the right client.'.format(
                    clientAPI, serverAPI, __version__
                ),
            ]

        if self.authority.authoriseUser(user, password):
            # On token request also make sure anything "out" with that user is reset as todo.
            self.IDDB.resetUsersToDo(user)
            self.MDB.resetUsersToDo(user)
            self.TDB.resetUsersToDo(user)
            self.logger.info("Authorising user {}".format(user))
            return [True, self.authority.getToken(user)]
        else:
            return [False, "NAU"]

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
        shutil.copy(srcfile, dstfile)
        # Copy with full name (not just directory) so can overwrite properly - else error on overwrite.

    def removeFile(self, davfn):
        """Once a file has been grabbed by the client, delete it from the webdav.
        """
        # delete file if present.
        fname = davDirectory + "/" + davfn
        if os.path.isfile(davDirectory + "/" + davfn):
            os.unlink(fname)

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

    def MgetPageGroupMax(self, pg, v):
        """When a marked-client logs on they need the max mark for the group
        they are marking. Check the (group/version) is valid and then send back
        the corresponding mark from the test spec.
        """
        iv = int(v)
        ipg = int(pg)
        if ipg < 1 or ipg > self.testSpec.getNumberOfGroups():
            return [False, "PGE"]
        if iv < 1 or iv > self.testSpec.Versions:
            return [False, "VE"]
        # Send an ack with the max-mark for the pagegroup.
        return [True, self.testSpec.Marks[ipg]]

    def IDdidntFinish(self, user, code):
        """User didn't finish IDing the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.IDDB.didntFinish(user, code)
        return

    def MdidntFinish(self, user, tgv):
        """User didn't finish marking the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.MDB.didntFinish(user, tgv)
        return

    def TdidntFinish(self, user, code):
        """User didn't finish totaling the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.TDB.didntFinish(user, code)
        return

    def userClosing(self, user):
        """Client is closing down their app, so remove the authorisation token
        """
        self.authority.detoken(user)

    def IDaskNextTask(self, user):
        """The client has asked for the next unidentified paper, so
        ask the database for its code and send back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.IDDB.askNextTask(user)
        if give is None:
            return [False]
        else:
            # Send to the client
            return [True, give]

    def IDclaimSpecificTask(self, user, code):
        if self.IDDB.giveSpecificTaskToClient(user, code):
            # return true, image-filename
            return [True, "{}/idgroup/{}.png".format(pathScanDirectory, code)]
        else:
            # return a fail claim - client will try again.
            return [False]

    def IDprogressCount(self):
        """Send back current ID progress counts to the client"""
        return [self.IDDB.countIdentified(), self.IDDB.countAll()]

    def IDreturnIDd(self, user, ret, sid, sname):
        """Client has ID'd the pageimage with code=ret, student-number=sid,
        and student-name=sname. Send the information to the database (which
        checks if that number has been used previously). If okay then send
        and ACK, else send an error that the number has been used.
        """
        # TODO - improve this
        # returns [True] if all good
        # [False, True] - if student number already in use
        # [False, False] - if bigger error
        return self.IDDB.takeIDImageFromClient(ret, user, sid, sname)

    def IDgetAlreadyIDList(self, user):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list.
        """
        return self.IDDB.buildIDList(user)

    def IDgetGroupImage(self, user, tgv):
        if self.IDDB.getGroupImage(user, tgv):
            fname = "{}/idgroup/{}.png".format(pathScanDirectory, tgv)
            return [True, fname]
        else:
            return [False]

    def MaskNextTask(self, user, pg, v):
        """The client has asked for the next unmarked paper, so
        ask the database for its code and send back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.MDB.askNextTask(user, pg, v)
        if give is None:
            return [False]
        else:
            # Send to the client
            return [True, give]

    def MclaimSpecificTask(self, user, code):
        return self.MDB.giveSpecificTaskToClient(user, code)
        # retval is either [False] or [True, fname, tags]

    def MprogressCount(self, pg, v):
        """Send back current marking progress counts to the client"""
        return [self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

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
        # sanity check that mark lies in [0,..,max]
        if int(mark) < 0 or int(mark) > self.testSpec.Marks[int(pg)]:
            # this should never happen.
            return ["ERR", "Assigned mark out of range. Contact administrator."]
        if not (
            code.startswith("t")
            and fname == "G{}.png".format(code[1:])
            and pname == "G{}.plom".format(code[1:])
            and cname == "G{}.json".format(code[1:])
        ):
            SLogger.info(
                "Rejected mismatched files from buggy client (user {}) for {}".format(
                    user, code
                )
            )
            return ["ERR", "Buggy client gave me the wrong files!  File a bug."]

        # move annoted file to right place with new filename
        self.claimFile(fname, "")
        self.claimFile(pname, "plomFiles")
        self.claimFile(cname, "commentFiles")
        # Should check the fname is valid png - just check header presently
        if imghdr.what(os.path.join("markedPapers", fname)) != "png":
            return ["ERR", "Misformed image file. Try again."]
        # now update the database
        self.MDB.takeGroupImageFromClient(
            code, user, mark, fname, pname, cname, mtime, tags
        )
        self.recordMark(user, mark, fname, mtime, tags)
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

    def MgetMarkedList(self, user, pg, v):
        """When a marked-client logs on they request a list of papers they have already marked.
        Check the (group/version) is valid and then send back a textfile with list of TGVs.
        """
        iv = int(v)
        ipg = int(pg)
        # TODO - verify that since this happens after "get max mark" we don't need to check ranges - they should be fine unless real idiocy has happened?
        return self.MDB.buildMarkedList(user, pg, v)

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

    def MlatexThisText(self, user, fragment):
        # TODO - only one frag file per user - is this okay?
        tfrag = tempfile.NamedTemporaryFile()
        with open(tfrag.name, "w+") as fh:
            fh.write(fragment)

        fname = os.path.join(tempDirectory.name, "{}_frag.png".format(user))
        if (
            subprocess.run(["python3", "latex2png.py", tfrag.name, fname]).returncode
            == 0
        ):
            return [True, fname]
        else:
            return [False]

    def TgetMaxMark(self):
        return sum(spec.Marks)

    def TaskNextTask(self, user):
        """The client has asked for the next unidentified paper, so
        ask the database for its code and send back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.TDB.askNextTask(user)
        if give is None:
            return [False]
        else:
            # Send to the client
            return [True, give]

    def TclaimSpecificTask(self, user, code):
        if self.TDB.giveSpecificTaskToClient(user, code):
            # return true, image-filename
            return [True, "{}/idgroup/{}.png".format(pathScanDirectory, code)]
        else:
            # return a fail claim - client will try again.
            return [False]

    def TgotTest(self, user, token, test, tfn):
        """Client acknowledges they got the test pageimage, so server
        deletes it from the webdav and sends an ack.
        """
        self.removeFile(tfn)
        return ["ACK"]

    def TprogressCount(self):
        """Send back current total progress counts to the client"""
        return [self.TDB.countTotaled(), self.TDB.countAll()]

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

    def TreturnTotaled(self, user, ret, value):
        """Client has totaled the pageimage with code=ret, total=value.
        Send the information to the database and return an ACK
        """
        return self.TDB.takeTotalImageFromClient(ret, user, value)

    def TgetAlreadyTotaledList(self, user):
        """When a total-client logs on they request a list of papers they have already totaled.
        Send back a list of TGVs.
        """
        return self.TDB.buildTotalList(user)

    def TdoneWithFile(self, user, token, tfn):
        """The client acknowledges they got the file,
        so the server deletes it and sends back an ACK.
        """
        self.removeFile(tfn)
        return ["ACK"]

    def TgetGroupImage(self, user, tgv):
        if self.TDB.getGroupImage(user, tgv):
            fname = "{}/idgroup/{}.png".format(pathScanDirectory, tgv)
            return [True, fname]
        else:
            return [False]


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
        exit(1)

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
        exit(1)


def checkDirectories():
    if not os.path.isdir("markedPapers"):
        os.mkdir("markedPapers")
    if not os.path.isdir("markedPapers/plomFiles"):
        os.mkdir("markedPapers/plomFiles")
    if not os.path.isdir("markedPapers/commentFiles"):
        os.mkdir("markedPapers/commentFiles")


print("Plom Server v{}: this is free software without warranty".format(__version__))
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
try:
    webdavlog = open("webdav.log", "w+")
except:
    print("Cannot open webdav.log filehandle.")
    exit()
# consider using "-q" option since it reduces verbosity of log and only keeps warnings+errors.
cmd = "wsgidav -H {} -p {} --server cheroot -r {} -c ../resources/davconf.yaml".format(
    serverInfo["server"], serverInfo["wport"], davDirectory
)
davproc = subprocess.Popen(shlex.split(cmd), stdout=webdavlog, stderr=webdavlog)

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

try:
    # Run the server
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, ssl_context=sslContext, port=serverInfo["mport"])
except KeyboardInterrupt:
    pass

# # # # # # # # # # # #
# Close the webdav server
subprocess.Popen.kill(davproc)
SLogger.info("Webdav server closed")
print("Webdav server closed")
webdavlog.close()
# close the rest of the stuff
SLogger.info("Closing databases")
print("Closing databases")
theIDDB.saveIdentified()
theMarkDB.saveMarked()
theTotalDB.saveTotaled()
