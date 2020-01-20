__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from aiohttp import web, MultipartWriter, MultipartReader
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
serverInfo = {"server": "127.0.0.1", "mport": 41984}
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


# ----------------------
# ----------------------
# Authentication / closing stuff


@routes.get("/Version")
async def version(request):
    return web.Response(
        text="Running Plom server version {} with API {}".format(
            __version__, serverAPI
        ),
        status=200,
    )


@routes.delete("/users/{user}")
async def closeUser(request):
    data = await request.json()
    user = request.match_info["user"]
    if data["user"] != request.match_info["user"]:
        return web.Response(status=400)  # malformed request.
    elif peon.validate(data["user"], data["token"]):
        peon.closeUser(data["user"])
        return web.Response(status=200)
    else:
        return web.Response(status=401)


@routes.put("/users/{user}")
async def giveUserToken(request):
    data = await request.json()
    user = request.match_info["user"]

    rmsg = peon.giveUserToken(data["user"], data["pw"], data["api"])
    if rmsg[0]:
        return web.json_response(rmsg[1], status=200)  # all good, return the token
    elif rmsg[1].startswith("API"):
        return web.json_response(
            rmsg[1], status=400
        )  # api error - return the error message
    else:
        return web.Response(status=401)  # you are not authorised


@routes.put("/admin/reloadUsers")
async def adminReloadUsers(request):
    data = await request.json()

    rmsg = peon.reloadUsers(data["pw"])
    # returns either True (success) or False (auth-error)
    if rmsg:
        return web.json_response(status=200)  # all good
    else:
        return web.Response(status=401)  # you are not authorised


@routes.put("/admin/reloadScans")
async def adminReloadScans(request):
    data = await request.json()

    rmsg = peon.reloadImages(data["pw"])
    # returns either True (success) or False (auth-error)
    if rmsg:
        return web.json_response(status=200)  # all good
    else:
        return web.Response(status=401)  # you are not authorised


# ----------------------
# ----------------------
# Test information
@routes.get("/info/shortName")
async def InfoShortName(request):
    if spec is not None:
        return web.Response(text=spec.Name, status=200)
    else:  # this should not happen
        return web.Response(status=404)


@routes.get("/info/numberOfGroupsAndVersions")
async def InfoPagesVersions(request):
    if spec is not None:
        return web.json_response([spec.getNumberOfGroups(), spec.Versions], status=200)
    else:  # this should not happen
        return web.Response(status=404)


@routes.get("/info/general")
async def InfoGeneral(request):
    if spec is not None:
        return web.json_response(
            [spec.Name, spec.Tests, spec.Length, spec.getNumberOfGroups(), spec.Versions],
            status=200,
        )
    else:  # this should not happen
        return web.Response(status=404)


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
async def IDaskNextTask(request):
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
async def IDrequestClasslist(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        if os.path.isfile("../resources/classlist.csv"):
            return web.FileResponse("../resources/classlist.csv", status=200)
        else:
            return web.Response(status=404)
    else:
        return web.Response(status=401)


@routes.get("/ID/predictions")
async def IDrequestPredictions(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        if os.path.isfile("../resources/predictionlist.csv"):
            return web.FileResponse("../resources/predictionlist.csv", status=200)
        else:
            return web.Response(status=404)
    else:
        return web.Response(status=401)


@routes.get("/ID/tasks/complete")
async def IDrequestDoneTasks(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(peon.IDrequestDoneTasks(data["user"]), status=200)
    else:
        return web.Response(status=401)


@routes.get("/ID/images/{tgv}")
async def IDrequestImage(request):
    data = await request.json()
    code = request.match_info["tgv"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.IDrequestImage(data["user"], code)
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
        rmesg = peon.IDclaimThisTask(data["user"], code)
        if rmesg[0]:  # return [True, filename]
            return web.FileResponse(rmesg[1], status=200)
        else:
            return web.Response(status=204)  # that task already taken.
    else:
        return web.Response(status=401)


@routes.put("/ID/tasks/{task}")
async def IDreturnIDdTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.IDreturnIDdTask(data["user"], code, data["sid"], data["sname"])
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
        peon.IDdidNotFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


# ----------------------
# ----------------------
# Totaller stuff


@routes.get("/TOT/maxMark")
async def TgetMarkMark(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        return web.json_response(peon.TgetMaxMark(), status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/tasks/complete")
async def TrequestDoneTasks(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(peon.TrequestDoneTasks(data["user"]), status=200)
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
async def TaskNextTask(request):
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
        rmesg = peon.TclaimThisTask(data["user"], code)
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
        peon.TdidNotFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


@routes.get("/TOT/images/{tgv}")
async def TrequestImage(request):
    data = await request.json()
    code = request.match_info["tgv"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.TrequestImage(data["user"], code)
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
async def TreturnTotaledTask(request):
    data = await request.json()
    code = request.match_info["task"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.TreturnTotaledTask(data["user"], code, data["mark"])
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
async def TgetMarkMark(request):
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
        peon.MdidNotFinish(data["user"], code)
        return web.json_response(status=200)
    else:
        return web.Response(status=401)


@routes.get("/MK/tasks/complete")
async def MrequestDoneTasks(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        # return the completed list
        return web.json_response(
            peon.MrequestDoneTasks(data["user"], data["pg"], data["v"]), status=200
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
async def MaskNextTask(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MaskNextTask(
            data["pg"], data["v"]
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
        rmesg = peon.MclaimThisTask(data["user"], code)
        if rmesg[0]:  # return [True, filename, tags]
            with MultipartWriter("imageAndTags") as mpwriter:
                mpwriter.append(open(rmesg[1], "rb"))
                mpwriter.append(rmesg[2])  # append tags as raw text.
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=204)  # that task already taken.
    else:
        return web.Response(status=401)


@routes.get("/MK/latex")
async def MlatexFragment(request):
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MlatexFragment(data["user"], data["fragment"])
        if rmsg[0]:  # user allowed access - returns [true, fname]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=406)  # a latex error
    else:
        return web.Response(status=401)  # not authorised at all


@routes.get("/MK/images/{tgv}")
async def MrequestImages(request):
    data = await request.json()
    code = request.match_info["tgv"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MrequestImages(data["user"], code)
        # returns either [True, fname] or [True, fname, aname, plomdat] or [False, error]
        if rmsg[0]:  # user allowed access - returns [true, fname]
            with MultipartWriter("imageAnImageAndPlom") as mpwriter:
                mpwriter.append(open(rmsg[1], "rb"))
                if len(rmsg) == 4:
                    mpwriter.append(open(rmsg[2], "rb"))
                    mpwriter.append(open(rmsg[3], "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=409)  # someone else has that image
    else:
        return web.Response(status=401)  # not authorised at all


@routes.get("/MK/originalImage/{test}/{group}")
async def MrequestOriginalImage(request):
    data = await request.json()
    testNumber = request.match_info["test"]
    pageGroup = request.match_info["group"]
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MrequestOriginalImage(testNumber, pageGroup)
        # returns either [True, fname] or [False]
        if rmsg[0]:  # user allowed access - returns [true, fname]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no content there
    else:
        return web.Response(status=401)  # not authorised at all


@routes.put("/MK/tasks/{tgv}")
async def MreturnMarkedTask(request):
    code = request.match_info["tgv"]
    # the put will be in 3 parts - use multipart reader
    # in order we expect those 3 parts - [parameters (inc comments), image, plom-file]
    reader = MultipartReader.from_response(request)
    part0 = await reader.next()
    if part0 is None:  # weird error
        return web.Response(status=406)  # should have sent 3 parts
    param = await part0.json()
    comments = param["comments"]

    # image file
    part1 = await reader.next()
    if part1 is None:  # weird error
        return web.Response(status=406)  # should have sent 3 parts
    image = await part1.read()

    # plom file
    part2 = await reader.next()
    if part2 is None:  # weird error
        return web.Response(status=406)  # should have sent 3 parts
    plomdat = await part2.read()

    if peon.validate(param["user"], param["token"]):
        rmsg = peon.MreturnMarkedTask(
            param["user"],
            code,
            int(param["pg"]),
            int(param["ver"]),
            int(param["score"]),
            image,
            plomdat,
            comments,
            int(param["mtime"]),
            param["tags"],
        )
        # rmsg = either [True, numDone, numTotal] or [False] if error.
        if rmsg[0]:
            return web.json_response([rmsg[1], rmsg[2]], status=200)
        else:
            return web.Response(status=400)  # some sort of error with image file
    else:
        return web.Response(status=401)  # not authorised at all


@routes.patch("/MK/tags/{tgv}")
async def MsetTag(request):
    code = request.match_info["tgv"]
    data = await request.json()
    if peon.validate(data["user"], data["token"]):
        rmsg = peon.MsetTag(data["user"], code, data["tags"])
        if rmsg:
            return web.Response(status=200)
        else:
            return web.Response(status=409)  # this is not your tgv
    else:
        return web.Response(status=401)  # not authorised at all


@routes.get("/MK/whole/{number}")
async def MrequestWholePaper(request):
    data = await request.json()
    number = request.match_info["number"]
    if peon.validate(data["user"], data["token"]):
        rmesg = peon.MrequestWholePaper(data["user"], number)
        if rmesg[0]:  # return [True, [filenames]] or [False]
            with MultipartWriter("imageAndTags") as mpwriter:
                for fn in rmesg[1]:
                    mpwriter.append(open(fn, "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=409)  # not yours
    else:
        return web.Response(status=401)


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
        # Load in the list of users who will run the client app.
        self.loadUsers()
        # check databases are set up and complete.
        if self.checkDatabases():
            print("Databases checked - complete.")
        else:
            print("Databases incomplete - repopulating.")
            self.repopulateDatabases()

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
            self.logger.info("Unauthorised attempt to reload images")
            return False
        self.logger.info("Reloading group images")
        # Read in the groups and images again.
        readExamsGrouped()
        findPageGroups()
        self.loadPapers()
        # Send acknowledgement back to manager.
        return True

    def reloadUsers(self, password):
        """Reload the user list."""
        # Check user is manager.
        if not self.authority.authoriseUser("Manager", password):
            self.logger.info("Unauthorised attempt to reload users")
            return False
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
        # return acknowledgement
        print(">> User list reloaded")
        return True

    def giveUserToken(self, user, password, clientAPI):
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
        # read exams-produced for case that papers already have SID/SNames stamped

        self.repopulateDatabases()
        # Send acknowledgement back to manager.
        return ["ACK"]

    def repopulateDatabases(self):
        """Load the IDgroup page images for identifying
        and the group-images for marking.
        The ID-images are stored in the IDDB, and the
        image for marking in the MDB.
        """
        self.logger.info("Repopulating databases with missing entries.")
        for t in sorted(examsGrouped.keys()):
            # the corresponding code:
            code = "t{:s}idg".format(t.zfill(4))
            # check the ID-database
            if not self.IDDB.checkExists(code):
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
                        int(t), code, examsProduced[t]["id"], examsProduced[t]["name"]
                    )
                else:
                    self.logger.info("Adding id group {}".format(code))
                    self.IDDB.addUnIDdExam(int(t), code)
            # check the total-database
            if not self.TDB.checkExists(code):
                self.TDB.addUntotaledExam(int(t), code)
                self.logger.info("Adding Total-image {}".format(code))

        for tgv in sorted(pageGroupsForGrading.keys()):
            if not self.MDB.checkExists(tgv):
                # tgv is t1234g67v9
                t, pg, v = int(tgv[1:5]), int(tgv[6:8]), int(tgv[9])
                self.MDB.addUnmarkedGroupImage(t, pg, v, tgv, pageGroupsForGrading[tgv])
                self.logger.info("Adding groupImage {}".format(tgv))

    def checkDatabases(self):
        """Check that each TGV is in the database"""
        flag = True
        idMiss = []
        tMiss = []
        mMiss = []
        for t in sorted(examsGrouped.keys()):
            code = "t{:s}idg".format(t.zfill(4))
            if not self.IDDB.checkExists(code):
                # print("ID database missing {}".format(code))
                idMiss.append(code)
                flag = False
            if not self.TDB.checkExists(code):
                # print("Total database missing {}".format(code))
                tMiss.append(code)
                flag = False
        for tgv in sorted(pageGroupsForGrading.keys()):
            if not self.MDB.checkExists(tgv):
                # print("Mark database missing {}".format(code))
                mMiss.append(tgv)
                flag = False
        if not flag:
            if len(idMiss) > 0:
                print("ID-database missing {}".format(idMiss))
            if len(tMiss) > 0:
                print("Total-database missing {}".format(tMiss))
            if len(mMiss) > 0:
                print("Mark-database missing {}".format(mMiss))
        return flag

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

    def IDdidNotFinish(self, user, code):
        """User didn't finish IDing the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.IDDB.didntFinish(user, code)
        return

    def MdidNotFinish(self, user, tgv):
        """User didn't finish marking the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.MDB.didntFinish(user, tgv)
        return

    def TdidNotFinish(self, user, code):
        """User didn't finish totaling the image with given code. Tell the
        database to put this back on the todo-pile.
        """
        self.TDB.didntFinish(user, code)
        return

    def closeUser(self, user):
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

    def IDclaimThisTask(self, user, code):
        if self.IDDB.giveSpecificTaskToClient(user, code):
            # return true, image-filename
            return [True, "{}/idgroup/{}.png".format(pathScanDirectory, code)]
        else:
            # return a fail claim - client will try again.
            return [False]

    def IDprogressCount(self):
        """Send back current ID progress counts to the client"""
        return [self.IDDB.countIdentified(), self.IDDB.countAll()]

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
        return self.IDDB.takeIDImageFromClient(ret, user, sid, sname)

    def IDrequestDoneTasks(self, user):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list.
        """
        return self.IDDB.buildIDList(user)

    def IDrequestImage(self, user, tgv):
        if self.IDDB.getGroupImage(user, tgv):
            fname = "{}/idgroup/{}.png".format(pathScanDirectory, tgv)
            return [True, fname]
        else:
            return [False]

    def MaskNextTask(self, pg, v):
        """The client has asked for the next unmarked paper, so
        ask the database for its code and send back to the
        client.
        """
        # Get code of next unidentified image from the database
        give = self.MDB.askNextTask(pg, v)
        if give is None:
            return [False]
        else:
            # Send to the client
            return [True, give]

    def MclaimThisTask(self, user, code):
        return self.MDB.giveSpecificTaskToClient(user, code)
        # retval is either [False] or [True, fname, tags]

    def MprogressCount(self, pg, v):
        """Send back current marking progress counts to the client"""
        return [self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

    def MreturnMarkedTask(
        self, user, code, pg, v, mark, image, plomdat, comments, mtime, tags
    ):
        """Client has marked the pageimage with code, mark, annotated-file-name
        and spent mtime marking it.
        Send the information to the database and send an ack.
        """
        # score + file sanity checks were done at client. Do we need to redo here?
        # image, plomdat are bytearrays, comments = list
        aname = "G{}.png".format(code[1:])
        pname = "G{}.plom".format(code[1:])
        cname = "G{}.json".format(code[1:])
        with open("markedPapers/" + aname, "wb") as fh:
            fh.write(image)
        with open("markedPapers/plomFiles/" + pname, "wb") as fh:
            fh.write(plomdat)
        with open("markedPapers/commentFiles/" + cname, "w") as fh:
            json.dump(comments, fh)

        # Should check the fname is valid png - just check header presently
        if imghdr.what("markedPapers/" + aname) != "png":
            return [False, "Misformed image file. Try again."]
        # now update the database
        self.MDB.takeGroupImageFromClient(
            code, user, mark, aname, pname, cname, mtime, tags
        )
        self.recordMark(user, mark, aname, mtime, tags)
        # return ack with current counts.
        return [True, self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

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

    def MrequestDoneTasks(self, user, pg, v):
        """When a marked-client logs on they request a list of papers they have already marked.
        Check the (group/version) is valid and then send back a textfile with list of TGVs.
        """
        iv = int(v)
        ipg = int(pg)
        # TODO - verify that since this happens after "get max mark" we don't need to check ranges - they should be fine unless real idiocy has happened?
        return self.MDB.buildMarkedList(user, pg, v)

    def MrequestImages(self, user, tgv):
        give, fname, aname = self.MDB.getGroupImage(user, tgv)
        if fname is not None:
            if aname is not None:
                # plom file is same as annotated file just with suffix plom
                return [
                    True,
                    fname,
                    "markedPapers/" + aname,
                    "markedPapers/plomFiles/" + aname[:-3] + "plom",
                ]
            else:
                return [True, fname]
        else:
            return [False]

    def MrequestOriginalImage(self, testNumber, pageGroup):
        fname = self.MDB.getOriginalGroupImage(testNumber, pageGroup)
        if fname is not None:
            return [True, fname]
        else:
            return [False]

    def MsetTag(self, user, tgv, tag):
        if self.MDB.setTag(user, tgv, tag):
            return True
        else:
            return False

    def MrequestWholePaper(self, user, testNumber):
        # client passes the tgv code of their current group image.
        # from this we infer the test number.
        files = self.MDB.getTestAll(testNumber)
        if len(files) > 0:
            return [True, files]
        else:
            return [False]

    def MlatexFragment(self, user, fragment):
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

    def TclaimThisTask(self, user, code):
        if self.TDB.giveSpecificTaskToClient(user, code):
            # return true, image-filename
            return [True, "{}/idgroup/{}.png".format(pathScanDirectory, code)]
        else:
            # return a fail claim - client will try again.
            return [False]

    def TprogressCount(self):
        """Send back current total progress counts to the client"""
        return [self.TDB.countTotaled(), self.TDB.countAll()]

    def TreturnTotaledTask(self, user, ret, value):
        """Client has totaled the pageimage with code=ret, total=value.
        Send the information to the database and return an ACK
        """
        return self.TDB.takeTotalImageFromClient(ret, user, value)

    def TrequestDoneTasks(self, user):
        """When a total-client logs on they request a list of papers they have already totaled.
        Send back a list of TGVs.
        """
        return self.TDB.buildTotalList(user)

    def TrequestImage(self, user, tgv):
        if self.TDB.getGroupImage(user, tgv):
            fname = "{}/idgroup/{}.png".format(pathScanDirectory, tgv)
            return [True, fname]
        else:
            return [False]


# # # # # # # # # # # #
# # # # # # # # # # # #


def checkPortFree(ip, port):
    """Test if the given port is free so server can use it."""
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
    """Check that the messaging port is free on the server."""
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

tempDirectory = tempfile.TemporaryDirectory()
# Give directory correct permissions.
subprocess.check_call(["chmod", "o-r", tempDirectory.name])

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
peon = Server(theIDDB, theMarkDB, theTotalDB, spec, SLogger)

try:
    # Run the server
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, ssl_context=sslContext, port=serverInfo["mport"])
except KeyboardInterrupt:
    pass

# close the rest of the stuff
SLogger.info("Closing databases")
print("Closing databases")
theIDDB.saveIdentified()
theMarkDB.saveMarked()
theTotalDB.saveTotaled()
