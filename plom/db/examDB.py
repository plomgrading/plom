# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

from datetime import datetime, timedelta

from peewee import *

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName


import logging

log = logging.getLogger("DB")

from plom.db.tables import *

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
                    Bundle,
                    Test,
                    ##
                    Group,
                    IDGroup,
                    DNMGroup,
                    QGroup,
                    ##
                    TPage,
                    HWPage,
                    EXPage,
                    LPage,
                    UnknownPage,
                    CollidingPage,
                    DiscardedPage,
                    ##
                    AImage,
                    Annotation,
                    OldAnnotation,
                    ##
                    APage,
                    OAPage,
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
        doesBundleExist,
        createNewBundle,
        createReplacementBundle,
        areAnyPapersProduced,
        nextqueue_position,
        createTest,
        addTPages,
        createIDGroup,
        createDNMGroup,
        createQGroup,
        getPageVersions,
        produceTest,
        id_paper,
    )

    from plom.db.db_upload import (
        createNewImage,
        attachImageToTPage,
        createNewHWPage,
        createNewLPage,
        uploadTestPage,
        uploadHWPage,
        uploadLPage,
        uploadUnknownPage,
        uploadCollidingPage,
        updateDNMGroup,
        updateIDGroup,
        cleanIDGroup,
        updateQGroup,
        cleanQGroup,
        updateGroupAfterUpload,
        checkTestScanned,
        updateTestAfterUpload,
        processUpdatedTests,
        getSIDFromTest,
        sidToTest,
        replaceMissingHWQuestion,
        replaceMissingTestPage,
        removeAllScannedPages,
    )

    from plom.db.db_manage import (
        getUnknownPageNames,
        getDiscardNames,
        getCollidingPageNames,
        getTPageImage,
        getHWPageImage,
        getEXPageImage,
        getLPageImage,
        getAllTestImages,
        getQuestionImages,
        getUnknownImage,
        testOwnersLoggedIn,
        moveUnknownToExtraPage,
        moveUnknownToHWPage,
        moveUnknownToTPage,
        checkTPage,
        removeUnknownImage,
        getDiscardImage,
        moveDiscardToUnknown,
        moveUnknownToCollision,
        getCollidingImage,
        removeCollidingImage,
        moveCollidingToTPage,
    )

    from plom.db.db_report import (
        RgetScannedTests,
        RgetIncompleteTests,
        RgetCompleteHW,
        RgetMissingHWQ,
        RgetUnusedTests,
        RgetIdentified,
        RgetProgress,
        RgetMarkHistogram,
        RgetMarked,
        RgetQuestionUserProgress,
        RgetCompletionStatus,
        RgetOutToDo,
        RgetStatus,
        RgetSpreadsheet,
        RgetOriginalFiles,
        RgetCoverPageInfo,
        RgetAnnotatedFiles,
        RgetMarkReview,
        RgetAnnotatedImage,
        RgetIDReview,
        RgetUserFullProgress,
    )

    from plom.db.db_identify import (
        IDcountAll,
        IDcountIdentified,
        IDgetNextTask,
        IDgiveTaskToClient,
        IDgetDoneTasks,
        IDgetImage,
        IDgetImageByNumber,
        IDdidNotFinish,
        ID_id_paper,
        IDgetImageFromATest,
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
        MgetOneImageFilename,
        MgetOriginalImages,
        MsetTag,
        MgetWholePaper,
        MreviewQuestion,
        MrevertTask,
    )
