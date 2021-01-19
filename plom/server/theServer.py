# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

__copyright__ = "Copyright (C) 2019-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Dryden Wiebe", "Vala Vakilian"]
__license__ = "AGPLv3"

# TODO - directory structure!

import json
import ssl
import subprocess
import tempfile
import logging
from pathlib import Path

import toml
from aiohttp import web

from plom import __version__
from plom import Plom_API_Version as serverAPI
from plom import Default_Port
from plom import SpecVerifier
from plom import specdir
from plom.db import PlomDB

from .authenticate import Authority

serverInfo = {"server": "127.0.0.1", "port": Default_Port}


from .plomServer.routesUserInit import UserInitHandler
from .plomServer.routesUpload import UploadHandler
from .plomServer.routesID import IDHandler
from .plomServer.routesMark import MarkHandler
from .plomServer.routesReport import ReportHandler


confdir = Path("serverConfiguration")

# 5 is to keep debug/info lined up
logging.basicConfig(
    format="%(asctime)s %(levelname)5s:%(name)s\t%(message)s",
    datefmt="%b%d %H:%M:%S",
)
log = logging.getLogger("server")
# We will reset this later after we read the config
logging.getLogger().setLevel("Debug".upper())


# ----------------------
def build_directories():
    """Build the directories that this script needs"""

    # the list of directories. Might need updating.
    for d in (
        "pages",
        "pages/discardedPages",
        "pages/collidingPages",
        "pages/unknownPages",
        "pages/originalPages",
        "markedQuestions",
        "markedQuestions/plomFiles",
        "markedQuestions/commentFiles",
    ):
        Path(d).mkdir(exist_ok=True)
        log.debug("Building directory {}".format(d))


# ----------------------


class Server(object):
    def __init__(self, spec, db, masterToken):
        log.debug("Initialising server")
        self.testSpec = spec
        self.authority = Authority(masterToken)
        self.DB = db
        self.API = serverAPI
        self.Version = __version__
        print(
            "Server launching with masterToken = '{}' {}".format(
                self.authority.get_master_token(),
                type(self.authority.get_master_token()),
            )
        )
        self.tempDirectory = tempfile.TemporaryDirectory()
        # Give directory correct permissions.
        subprocess.check_call(["chmod", "o-r", self.tempDirectory.name])
        self.load_users()

    def load_users(self):
        """Load the users from json file, add them to the database and checks pwd hashes.

        It does simple sanity checks of pwd hashes to see if they have changed.
        """

        if (confdir / "userList.json").exists():
            with open(confdir / "userList.json") as data_file:
                # load list of users + pwd hashes
                userList = json.load(data_file)
                # for each name check if in DB by asking for the hash of its pwd
                for uname in userList.keys():
                    passwordHash = self.DB.getUserPasswordHash(uname)
                    if passwordHash is None:  # not in list
                        self.DB.createUser(uname, userList[uname])
                    else:
                        if passwordHash != userList[uname]:
                            log.warning("User {} password has changed.".format(uname))
                        self.DB.setUserPasswordHash(userList[uname], passwordHash)
            log.debug("Loading users")
        else:
            # Cannot find users - give error and quit out.
            log.error("Cannot find user/password file - aborting.")
            quit()

    from .plomServer.serverUserInit import (
        validate,
        checkPassword,
        checkUserEnabled,
        createModifyUser,
        InfoShortName,
        info_spec,
        reloadUsers,
        giveUserToken,
        setUserEnable,
        closeUser,
    )
    from .plomServer.serverUpload import (
        doesBundleExist,
        createNewBundle,
        sidToTest,
        addTestPage,
        addHWPage,
        addLPage,
        processHWUploads,
        processTUploads,
        processLUploads,
        addUnknownPage,
        addCollidingPage,
        replaceMissingTestPage,
        replaceMissingHWQuestion,
        removeAllScannedPages,
        getUnknownPageNames,
        getDiscardNames,
        getCollidingPageNames,
        getUnknownImage,
        getCollidingImage,
        getDiscardImage,
        getTPageImage,
        getHWPageImage,
        getEXPageImage,
        getLPageImage,
        getQuestionImages,
        getAllTestImages,
        checkTPage,
        removeUnknownImage,
        removeCollidingImage,
        unknownToTestPage,
        unknownToHWPage,
        unknownToExtraPage,
        collidingToTestPage,
        discardToUnknown,
    )
    from .plomServer.serverID import (
        IDprogressCount,
        IDgetNextTask,
        IDgetDoneTasks,
        IDgetImage,
        IDgetImageFromATest,
        IDclaimThisTask,
        IDdidNotFinish,
        id_paper,
        ID_id_paper,
        IDdeletePredictions,
        IDrunPredictions,
        IDreviewID,
    )
    from .plomServer.serverMark import (
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
        MrevertTask,
    )

    from .plomServer.serverReport import (
        RgetUnusedTests,
        RgetScannedTests,
        RgetIncompleteTests,
        RgetCompleteHW,
        RgetMissingHWQ,
        RgetProgress,
        RgetQuestionUserProgress,
        RgetMarkHistogram,
        RgetMarked,
        RgetIdentified,
        RgetCompletionStatus,
        RgetOutToDo,
        RgetStatus,
        RgetSpreadsheet,
        RgetCoverPageInfo,
        RgetOriginalFiles,
        RgetAnnotatedFiles,
        RgetMarkReview,
        RgetIDReview,
        RgetAnnotatedImage,
        RgetUserList,
        RgetUserDetails,
    )


def get_server_info():
    """Read the server info from config file."""

    global serverInfo
    try:
        with open(confdir / "serverDetails.toml") as data_file:
            serverInfo = toml.load(data_file)
            logging.getLogger().setLevel(serverInfo["LogLevel"].upper())
            log.debug("Server details loaded: {}".format(serverInfo))
    except FileNotFoundError:
        log.warning("Cannot find server details, using defaults")
    # Special treatment for chatty modules
    # TODO: nicer way to do this?
    if serverInfo["LogLevel"].upper() == "INFO":
        logging.getLogger("aiohttp.access").setLevel("WARNING")


def launch(masterToken=None):
    """Launches the Plom server.

    Keyword Arguments:
        masterToken {str} -- Token that is authenticated by the authority, if None, one is created in authenticate.py. default: {None}
    """

    log.info("Plom Server {} (communicates with api {})".format(__version__, serverAPI))
    get_server_info()
    examDB = PlomDB(Path(specdir) / "plom.db")
    # TODO: might be nice to do a sanity spec verification, once we have a quiet one
    spec = SpecVerifier.from_toml_file(Path(specdir) / "verifiedSpec.toml")
    build_directories()
    peon = Server(spec, examDB, masterToken)
    userIniter = UserInitHandler(peon)
    uploader = UploadHandler(peon)
    ider = IDHandler(peon)
    marker = MarkHandler(peon)
    reporter = ReportHandler(peon)

    # construct the web server
    app = web.Application()
    log.info("Setting up routes")
    userIniter.setUpRoutes(app.router)
    uploader.setUpRoutes(app.router)
    ider.setUpRoutes(app.router)
    marker.setUpRoutes(app.router)
    reporter.setUpRoutes(app.router)
    log.info("Loading ssl context")
    sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    sslContext.check_hostname = False
    sslContext.load_cert_chain(confdir / "plom-selfsigned.crt", confdir / "plom.key")
    log.info("Start the server!")
    try:
        web.run_app(app, ssl_context=sslContext, port=serverInfo["port"])
    except KeyboardInterrupt:
        # Above seems to have its own Ctrl-C handler so this never happens?
        log.info("Closing down via keyboard interrupt")
