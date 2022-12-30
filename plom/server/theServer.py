# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Natalie Balashov

import json
import logging
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile

import arrow
from aiohttp import web

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from plom import __version__
from plom import Plom_API_Version as serverAPI
from plom import Default_Port
from plom import SpecVerifier
from plom.aliceBob import simple_password
from plom.db import PlomDB
from plom.server import specdir, confdir, check_server_directories
from plom.misc_utils import working_directory

from .authenticate import Authority

from .plomServer import (
    IDHandler,
    MarkHandler,
    ReportHandler,
    RubricHandler,
    SolutionHandler,
    UploadHandler,
    UserInitHandler,
)


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
        if not self.DB.doesUserExist("manager"):
            log.info("No manager password: autogenerating and writing to stdout...")
            manager_pw = simple_password(n=6)
            print(f"Initial manager password: {manager_pw}")
            hashpw = self.authority.create_password_hash(manager_pw)
            del manager_pw
            assert self.DB.createUser("manager", hashpw)

    def load_users(self):
        """Load the users from json file, add them to the database and checks pwd hashes.

        It does simple sanity checks of pwd hashes to see if they have changed.
        """
        log = logging.getLogger("server")
        init_user_list = confdir / "bootstrap_initial_users.json"
        if not init_user_list.exists():
            log.info(f'"{init_user_list}" not found: skipping')
            return
        log.info(f'Loading users from "{init_user_list}"')
        with open(init_user_list) as data_file:
            # load list of users + pwd hashes
            userList = json.load(data_file)
        for user, pw in userList.items():
            if self.DB.doesUserExist(user):
                log.warning("User %s already exists: not updating password", user)
                continue
            self.DB.createUser(user, pw)
        # Or maybe we should just erase it:
        log.info(f'archived "{init_user_list}" to "{init_user_list}.done"')
        init_user_list.rename(
            init_user_list.with_suffix(init_user_list.suffix + ".done")
        )

    from .plomServer.serverUserInit import (
        validate,
        checkPassword,
        checkUserEnabled,
        createUser,
        changeUserPassword,
        InfoShortName,
        info_spec,
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
        getUnknownPages,
        getDiscardedPages,
        getCollidingPageNames,
        getCollidingImage,
        getTPageImage,
        getHWPageImage,
        getEXPageImage,
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
        initialiseExamDatabase,
        appendTestToExamDatabase,
        getPageVersions,
        get_question_versions,
        get_all_question_versions,
    )
    from .plomServer.serverID import (
        IDprogressCount,
        IDgetNextTask,
        IDgetDoneTasks,
        IDgetImage,
        IDgetImageFromATest,
        ID_get_donotmark_images,
        IDclaimThisTask,
        add_or_change_predicted_id,
        remove_predicted_id,
        ID_id_paper,
        ID_get_predictions,
        ID_delete_predictions,
        ID_put_predictions,
        predict_id_lap_solver,
        predict_id_greedy,
        id_reader_get_log,
        id_reader_run,
        id_reader_kill,
        IDreviewID,
    )
    from .plomServer.serverMark import (
        MgetAllMax,
        MprogressCount,
        MgetDoneTasks,
        MgetNextTask,
        MlatexFragment,
        MclaimThisTask,
        MreturnMarkedTask,
        checkTagTextValid,
        add_tag,
        remove_tag,
        MgetTagsOfTask,
        MgetAllTags,
        McreateNewTag,
        get_pagedata,
        get_pagedata_question,
        get_pagedata_context_question,
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
        getDanglingPages,
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
        getFilesInAllTests,
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
        with open(basedir / confdir / "serverDetails.toml", "rb") as data_file:
            serverInfo = tomllib.load(data_file)
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
        master_token (None/str): a 32 hex-digit string used to encrypt tokens
            in the database.  Not needed on server unless you want to
            hot-restart the server without requiring users to log-off
            and log-in again.  If None, a new token is created.
    """
    basedir = Path(basedir)
    if not logfile:
        # filename must not have ":" (forbidden on win32)
        # e.g., use "ZZZ" not "ZZ" as the latter has "+00:00"
        now = arrow.utcnow().format("YYYY-MM-DD_HH-mm-ss_ZZZ")
        logfile = basedir / f"plom-server-{now}.log"
    logfile = Path(logfile)
    # if just filename, make log in basedir
    if logfile.parent == Path("."):
        logfile = basedir / logfile
    # 5 is to keep debug/info lined up
    fmtstr = "%(asctime)s %(levelname)5s:%(name)s\t%(message)s"
    logging.basicConfig(format=fmtstr, datefmt="%b%d %H:%M:%S %Z", filename=logfile)
    if logconsole:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(fmtstr, datefmt="%b%d %H:%M:%S %Z"))
        logging.getLogger().addHandler(h)

    log = logging.getLogger("server")
    # We will reset this later after we read the config
    logging.getLogger().setLevel("Debug".upper())

    log.info("Plom Server {} (communicates with api {})".format(__version__, serverAPI))
    check_server_directories(basedir)
    server_info = get_server_info(basedir)
    log.info(f'Working from directory "{basedir}"')
    if not (basedir / specdir / "plom.db").exists():
        log.info("Database is not yet present: creating...")
    db_name = server_info.get("db_name", None)
    db_host = server_info.get("db_host", None)
    db_port = server_info.get("db_port", None)
    db_username = server_info.get("db_username", None)
    db_password = server_info.get("db_password", None)
    examDB = PlomDB(
        basedir / specdir / "plom.db",
        db_name=db_name,
        db_host=db_host,
        db_port=db_port,
        db_username=db_username,
        db_password=db_password,
    )

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
