# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

from datetime import datetime, timedelta

from peewee import *

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName


import logging

log = logging.getLogger("DB")

from plom.db.tables import (
    plomdb,
    User,
    Image,
    Test,
    SumData,
    Group,
    IDGroup,
    DNMGroup,
    QGroup,
    TPage,
    HWPage,
    LPage,
    UnknownPage,
    CollidingPage,
    DiscardedPage,
    ##
    Annotation,
    ##
    APage,
    IDPage,
    DNMPage,
)

######################################################################


class PlomDB:
    def __init__(self, dbfile_name="plom.db"):
        # can't handle pathlib?
        plomdb.init(str(dbfile_name))

        with plomdb:
            plomdb.create_tables(
                [
                    User,
                    Image,
                    Test,
                    ##
                    SumData,
                    ##
                    Group,
                    IDGroup,
                    DNMGroup,
                    QGroup,
                    ##
                    TPage,
                    HWPage,
                    LPage,
                    UnknownPage,
                    CollidingPage,
                    DiscardedPage,
                    ##
                    Annotation,
                    ##
                    APage,
                    IDPage,
                    DNMPage,
                ]
            )
        log.info("Database initialised.")
        # check if HAL has been created
        if User.get_or_none(name="HAL") is None:
            User.create(
                name="HAL",
                password=None,
                last_activity=datetime.now(),
                last_action="Created",
            )
            log.info("User 'HAL' created to do all our automated tasks.")

    ########### User stuff #############
    from plom.db.db_user import (
        createUser,
        doesUserExist,
        setUserPasswordHash,
        getUserPasswordHash,
        isUserEnabled,
        enableUser,
        disableUser,
        setUserToken,
        clearUserToken,
        getUserToken,
        userHasToken,
        validateToken,
        getUserList,
        getUserDetails,
        resetUsersToDo,
    )

    from plom.db.db_create import (
        areAnyPapersProduced,
        nextqueue_position,
        createTest,
        addTPages,
        createIDGroup,
        createDNMGroup,
        createQGroup,
        getPageVersions,
        produceTest,
    )

    from plom.db.db_upload import (
        checkTestAllUploaded,
        setGroupReady,
        checkGroupAllUploaded,
        replaceMissingPage,
        fileOfScannedPage,
        createDiscardedPage,
        removeScannedPage,
        invalidateDNMGroup,
        invalidateIDGroup,
        invalidateQGroup,
        uploadTestPage,
        uploadHWPage,
        uploadLPage,
        cleanIDGroup,
        cleanSData,
        cleanQGroup,
        processUpdatedIDGroup,
        processUpdatedDNMGroup,
        processUpdatedQGroup,
        processUpdatedSData,
        cleanIDGroup,
        processSpecificUpdatedTest,
        processUpdatedTests,
        replaceMissingHWQuestion,
        uploadUnknownPage,
        uploadCollidingPage,
        getUnknownPageNames,
        getDiscardNames,
        getCollidingPageNames,
        getTPageImage,
        getHWPageImage,
        getLPageImage,
        getUnknownImage,
        getDiscardImage,
        getCollidingImage,
        getQuestionImages,
        getTestImages,
        checkPage,
        checkUnknownImage,
        checkCollidingImage,
        removeUnknownImage,
        removeCollidingImage,
        moveUnknownToPage,
        moveUnknownToCollision,
        moveCollidingToPage,
        moveExtraToPage,
        moveDiscardToUnknown,
    )

    from plom.db.db_report import (
        RgetScannedTests,
        RgetIncompleteTests,
        RgetUnusedTests,
        RgetIdentified,
        RgetProgress,
        RgetMarkHistogram,
        RgetMarked,
        RgetQuestionUserProgress,
        RgetCompletions,
        RgetOutToDo,
        RgetStatus,
        RgetSpreadsheet,
        RgetOriginalFiles,
        RgetCoverPageInfo,
        RgetAnnotatedFiles,
        RgetMarkReview,
        RgetAnnotatedImage,
        RgetIDReview,
        RgetTotReview,
        RgetUserFullProgress,
    )

    from plom.db.db_identify import (
        IDcountAll,
        IDcountIdentified,
        IDgetNextTask,
        IDgiveTaskToClient,
        IDgetDoneTasks,
        IDgetImage,
        IDgetImageList,
        IDdidNotFinish,
        id_paper,
        IDgetRandomImage,
        IDreviewID,
    )

    from plom.db.db_mark import (
        McountAll,
        McountMarked,
        MgetDoneTasks,
        MgetNextTask,
        MgiveTaskToClient,
        MdidNotFinish,
        MtakeTaskFromClient,
        MgetImages,
        MgetOriginalImages,
        MsetTag,
        MgetWholePaper,
        MshuffleImages,
        MreviewQuestion,
        MrevertTask,
    )

    # ----- totaller stuff
    from plom.db.db_total import (
        TcountTotalled,
        TcountAll,
        TgetNextTask,
        TgetDoneTasks,
        TgiveTaskToClient,
        TdidNotFinish,
        TgetImage,
        TtakeTaskFromClient,
    )
