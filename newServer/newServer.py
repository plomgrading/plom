__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

# TODO - directory structure!

# ----------------------

from aiohttp import web
import hashlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
import uuid

# ----------------------

from authenticate import Authority

# this allows us to import from ../resources
sys.path.append("..")
from resources.version import __version__
from resources.version import Plom_API_Version as serverAPI
from resources.specParser import SpecParser
from resources.examDB import *
from resources.logIt import printLog

# ----------------------

serverInfo = {"server": "127.0.0.1", "mport": 41984}
# ----------------------
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
sslContext.load_cert_chain("../resources/mlp-selfsigned.crt", "../resources/mlp.key")


from plomServer.routesUserInit import UserInitHandler
from plomServer.routesUpload import UploadHandler
from plomServer.routesID import IDHandler
from plomServer.routesMark import MarkHandler
from plomServer.routesTotal import TotalHandler
from plomServer.routesReport import ReportHandler

# ----------------------
def buildDirectories():
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = [
        "pages",
        "pages/discardedPages",
        "pages/collidingPages",
        "pages/unknownPages",
        "pages/originalPages",
        "markedQuestions",
        "markedQuestions/plomFiles",
        "markedQuestions/commentFiles",
    ]
    for dir in lst:
        try:
            os.mkdir(dir)
            printLog("Server", "Building directory {}".format(dir))
        except FileExistsError:
            pass


# ----------------------


class Server(object):
    def __init__(self, spec, db):
        printLog("Server", "Initialising server")
        self.testSpec = spec
        self.DB = db
        self.API = serverAPI
        self.Version = __version__
        self.tempDirectory = tempfile.TemporaryDirectory()
        # Give directory correct permissions.
        subprocess.check_call(["chmod", "o-r", self.tempDirectory.name])
        self.loadUsers()

    def loadUsers(self):
        """Load the users from json file, add them to the authority which
        handles authentication for us.
        """
        if os.path.exists("../resources/userList.json"):
            with open("../resources/userList.json") as data_file:
                # Load the users and pass them to the authority.
                self.userList = json.load(data_file)
                self.authority = Authority(self.userList)
            printLog("Server", "Loading users")
        else:
            # Cannot find users - give error and quit out.
            printLog("Server", "Cannot find user/password file - aborting.")
            quit()

    def validate(self, user, token):
        """Check the user's token is valid"""
        # printLog("Server", "Validating user {}.".format(user))
        return self.authority.validateToken(user, token)

    from plomServer.serverUserInit import (
        InfoShortName,
        InfoGeneral,
        reloadUsers,
        giveUserToken,
        closeUser,
    )
    from plomServer.serverUpload import (
        addKnownPage,
        addUnknownPage,
        addCollidingPage,
        replaceMissingPage,
        removeScannedPage,
        getUnknownPageNames,
        getDiscardNames,
        getCollidingPageNames,
        getUnknownImage,
        getCollidingImage,
        getDiscardImage,
        getPageImage,
        getQuestionImages,
        getTestImages,
        checkPage,
        removeUnknownImage,
        removeCollidingImage,
        unknownToTestPage,
        unknownToExtraPage,
        collidingToTestPage,
        discardToUnknown,
    )
    from plomServer.serverID import (
        IDprogressCount,
        IDgetNextTask,
        IDgetDoneTasks,
        IDgetImage,
        IDgetRandomImage,
        IDclaimThisTask,
        IDdidNotFinish,
        IDreturnIDdTask,
        IDdeletePredictions,
        IDreviewID,
    )
    from plomServer.serverMark import (
        MgetAllMax,
        MprogressCount,
        MgetQuestionMax,
        MgetDoneTasks,
        MgetNextTask,
        MlatexFragment,
        MclaimThisTask,
        MdidNotFinish,
        MrecordMark,
        MreturnMarkedTask,
        MgetImages,
        MgetOriginalImages,
        MsetTag,
        MgetWholePaper,
        MreviewQuestion,
    )
    from plomServer.serverTotal import (
        TgetMaxMark,
        TprogressCount,
        TgetDoneTasks,
        TgetNextTask,
        TclaimThisTask,
        TgetImage,
        TreturnTotalledTask,
        TdidNotFinish,
    )

    from plomServer.serverReport import (
        RgetUnusedTests,
        RgetScannedTests,
        RgetIncompleteTests,
        RgetProgress,
        RgetQuestionUserProgress,
        RgetMarkHistogram,
        RgetIdentified,
        RgetCompletions,
        RgetStatus,
        RgetSpreadsheet,
        RgetCoverPageInfo,
        RgetOriginalFiles,
        RgetAnnotatedFiles,
        RgetMarkReview,
        RgetIDReview,
        RgetTotReview,
        RgetAnnotatedImage,
        RgetUserList,
        RgetUserDetails,
    )


def getServerInfo():
    """Read the server info from json."""
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open("../resources/serverDetails.json") as data_file:
            serverInfo = json.load(data_file)
            printLog("Server", "Server details loaded: {}".format(serverInfo))
    else:
        printLog("Server", "Cannot find server details.")


getServerInfo()
examDB = PlomDB()
spec = SpecParser().spec
buildDirectories()
peon = Server(spec, examDB)
userIniter = UserInitHandler(peon)
uploader = UploadHandler(peon)
ider = IDHandler(peon)
marker = MarkHandler(peon)
totaller = TotalHandler(peon)
reporter = ReportHandler(peon)

try:
    # construct the web server
    app = web.Application()
    # add the routes
    printLog("Server", "Setting up routes")
    userIniter.setUpRoutes(app.router)
    uploader.setUpRoutes(app.router)
    ider.setUpRoutes(app.router)
    marker.setUpRoutes(app.router)
    totaller.setUpRoutes(app.router)
    reporter.setUpRoutes(app.router)
    # run the web server
    printLog("Server", "Start the server!")
    web.run_app(app, ssl_context=sslContext, port=serverInfo["mport"])
except KeyboardInterrupt:
    printLog("Server", "Closing down")
    pass
