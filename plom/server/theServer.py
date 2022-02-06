# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Peter Lee

from datetime import datetime
import json
import logging
from pathlib import Path
import ssl
import subprocess
import tempfile

import toml
from aiohttp import web

from plom import __version__
from plom import Plom_API_Version as serverAPI
from plom import Default_Port
from plom import SpecVerifier
from plom.db import PlomDB
from plom.server import specdir, confdir, check_server_directories

from .authenticate import Authority


from .plomServer.routesUserInit import UserInitHandler
from .plomServer.routesUpload import UploadHandler
from .plomServer.routesID import IDHandler
from .plomServer.routesMark import MarkHandler
from .plomServer.routesRubric import RubricHandler
from .plomServer.routesReport import ReportHandler
from .plomServer.routesSolution import SolutionHandler
from ..misc_utils import working_directory


class Server:
    def __init__(self, db, masterToken):
        log = logging.getLogger("server")
        log.debug("Initialising server")
        try:
            self.testSpec = SpecVerifier.load_verified()
            log.info("existing spec loaded")
        except FileNotFoundError:
            self.testSpec = None
            log.info("no spec file: we expect it later...")
        self.authority = Authority(masterToken)
        self.DB = db
        self.API = serverAPI
        self.Version = __version__
        # TODO: is leaky to have this token in the log/stdout?
        log.info(
            'Server launching with masterToken = "{}"'.format(
                self.authority.get_master_token(),
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
        log = logging.getLogger("server")
        if not (confdir / "userList.json").exists():
            raise FileNotFoundError("Cannot find user/password file.")
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
        createIDPageForHW,
        createDNMPagesForHW,
        addHWPage,
        addUnknownPage,
        addCollidingPage,
        replaceMissingTestPage,
        replaceMissingHWQuestion,
        replaceMissingDNMPage,
        replaceMissingIDPage,
        autogenerateIDPage,
        removeAllScannedPages,
        removeSinglePage,
        getUnknownPageNames,
        getDiscardNames,
        getCollidingPageNames,
        getUnknownImage,
        getCollidingImage,
        getDiscardImage,
        getTPageImage,
        getHWPageImage,
        getEXPageImage,
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
        listBundles,
        getBundleFromImage,
        getImagesInBundle,
        getPageFromBundle,
    )
    from .plomServer.serverID import (
        IDprogressCount,
        IDgetNextTask,
        IDgetDoneTasks,
        IDgetImage,
        IDgetImageFromATest,
        ID_get_donotmark_images,
        IDclaimThisTask,
        id_paper,
        ID_id_paper,
        IDdeletePredictions,
        IDputPredictions,
        IDrunPredictions,
        IDreviewID,
    )
    from .plomServer.serverMark import (
        MgetAllMax,
        MprogressCount,
        MgetDoneTasks,
        MgetNextTask,
        MlatexFragment,
        MclaimThisTask,
        MrecordMark,
        MreturnMarkedTask,
        MgetOriginalImages,
        checkTagTextValid,
        add_tag,
        remove_tag,
        MgetTagsOfTask,
        MgetAllTags,
        McreateNewTag,
        MgetWholePaper,
        MreviewQuestion,
        MrevertTask,
    )
    from .plomServer.serverRubric import (
        McreateRubric,
        MgetRubrics,
        MmodifyRubric,
        MgetUserRubricPanes,
        MsaveUserRubricPanes,
        RgetTestRubricMatrix,
        RgetRubricCounts,
        RgetRubricDetails,
    )
    from .plomServer.serverReport import (
        RgetUnusedTests,
        RgetScannedTests,
        RgetIncompleteTests,
        RgetDanglingPages,
        RgetCompleteHW,
        RgetMissingHWQ,
        RgetProgress,
        RgetQuestionUserProgress,
        RgetMarkHistogram,
        RgetIdentified,
        RgetNotAutoIdentified,
        RgetCompletionStatus,
        RgetOutToDo,
        RgetStatus,
        RgetSpreadsheet,
        RgetCoverPageInfo,
        RgetOriginalFiles,
        RgetMarkReview,
        RgetIDReview,
        RgetUserList,
        RgetUserDetails,
    )
    from .plomServer.serverSolution import (
        uploadSolutionImage,
        getSolutionImage,
        deleteSolutionImage,
        getSolutionStatus,
    )


def get_server_info(basedir):
    """Read the server info from config file."""

    log = logging.getLogger("server")
    serverInfo = {"server": "127.0.0.1", "port": Default_Port}
    try:
        with open(basedir / confdir / "serverDetails.toml") as data_file:
            serverInfo = toml.load(data_file)
            logging.getLogger().setLevel(serverInfo["LogLevel"].upper())
            log.debug("Server details loaded: {}".format(serverInfo))
    except FileNotFoundError:
        log.warning("Cannot find server details, using defaults")
    # Special treatment for chatty modules
    # TODO: nicer way to do this?
    if serverInfo["LogLevel"].upper() == "INFO":
        logging.getLogger("aiohttp.access").setLevel("WARNING")
    return serverInfo


def launch(basedir=Path("."), *, master_token=None, logfile=None, logconsole=True):
    """Launches the Plom server.

    args:
        basedir (pathlib.Path/str): the directory containing the file
            space to be used by this server.
        logfile (pathlib.Path/str/None): name-only then relative to basedir else
            If omitted, use a default name with date and time included.
        logconsole (bool): if True (default) then log to the stderr.
        master_token (str): a 32 hex-digit string used to encrypt tokens
            in the database.  Not needed on server unless you want to
            hot-restart the server without requiring users to log-off
            and log-in again.  If None, a new token is created.
    """
    basedir = Path(basedir)
    if not logfile:
        logfile = basedir / datetime.now().strftime("plomserver-%Y%m%d_%H-%M-%S.log")
    logfile = Path(logfile)
    # if just filename, make log in basedir
    if logfile.parent == Path("."):
        logfile = basedir / logfile
    # 5 is to keep debug/info lined up
    fmtstr = "%(asctime)s %(levelname)5s:%(name)s\t%(message)s"
    logging.basicConfig(format=fmtstr, datefmt="%b%d %H:%M:%S %Z", filename=logfile)
    if logconsole:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(fmtstr, datefmt="%b%d %H:%M:%S"))
        logging.getLogger().addHandler(h)

    log = logging.getLogger("server")
    # We will reset this later after we read the config
    logging.getLogger().setLevel("Debug".upper())

    log.info("Plom Server {} (communicates with api {})".format(__version__, serverAPI))
    check_server_directories(basedir)
    server_info = get_server_info(basedir)
    log.info(f'Working from directory "{basedir}"')
    if (basedir / specdir / "plom.db").exists():
        log.info("Using existing database.")
    else:
        log.info("Database is not yet present: creating...")
    examDB = PlomDB(basedir / specdir / "plom.db")
    if (basedir / specdir / "classlist.csv").exists():
        log.info("Classlist is present.")
    else:
        log.info("Cannot find the classlist: we expect it later...")
    with working_directory(basedir):
        peon = Server(examDB, master_token)
        userIniter = UserInitHandler(peon)
        uploader = UploadHandler(peon)
        ider = IDHandler(peon)
        marker = MarkHandler(peon)
        rubricker = RubricHandler(peon)
        reporter = ReportHandler(peon)
        solutioner = SolutionHandler(peon)

        # construct the web server
        app = web.Application()
        log.info("Setting up routes")
        userIniter.setUpRoutes(app.router)
        uploader.setUpRoutes(app.router)
        ider.setUpRoutes(app.router)
        marker.setUpRoutes(app.router)
        rubricker.setUpRoutes(app.router)
        reporter.setUpRoutes(app.router)
        solutioner.setUpRoutes(app.router)

    log.info("Loading ssl context")
    sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    sslContext.check_hostname = False
    try:
        sslContext.load_cert_chain(
            basedir / confdir / "plom-custom.crt", basedir / confdir / "plom-custom.key"
        )
        log.info("SSL: Loaded custom cert and key")
    except FileNotFoundError:
        try:
            sslContext.load_cert_chain(
                basedir / confdir / "plom-selfsigned.crt",
                basedir / confdir / "plom-selfsigned.key",
            )
            log.warning("SSL: Loaded default self-signed cert and key")
        except FileNotFoundError:
            raise FileNotFoundError(
                "Neither custom nor selfsigned cert/key found"
            ) from None
    log.info("Start the server!")
    with working_directory(basedir):
        web.run_app(app, ssl_context=sslContext, port=server_info["port"])
