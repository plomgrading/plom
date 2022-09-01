# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2022 Joey Shi

from datetime import datetime, timedelta, timezone
import logging

from plom.db.tables import *

from peewee import *

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName


log = logging.getLogger("DB")


class PlomDB:
    """The main Plom database."""

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
                    IDPrediction,
                    DNMGroup,
                    QGroup,
                    ##
                    TPage,
                    HWPage,
                    EXPage,
                    UnknownPage,
                    CollidingPage,
                    DiscardedPage,
                    ##
                    AImage,
                    Annotation,
                    ##
                    APage,
                    IDPage,
                    DNMPage,
                    ##
                    Rubric,
                    ARLink,
                    Tag,
                    QuestionTagLink,
                ]
            )
        log.info("Database initialised.")
        # check if HAL has been created
        if User.get_or_none(name="HAL") is None:
            # pylint: disable=no-member
            User.create(
                name="HAL",
                password=None,
                last_activity=datetime.now(timezone.utc),
                last_action="Created",
            )
            log.info("User 'HAL' created to do all our automated tasks.")

    # User stuff
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
        how_many_papers_in_database,
        is_paper_database_populated,
        is_paper_database_initialised,
        addSingleTestToDB,
        nextqueue_position,
        createTest,
        addTPages,
        createIDGroup,
        createDNMGroup,
        createQGroup,
        getPageVersions,
        get_question_versions,
        get_all_question_versions,
        add_or_change_id_prediction,
        remove_id_prediction,
        remove_id_from_paper,
        hasNoAnswerRubric,
        createNoAnswerRubric,
    )

    from plom.db.db_upload import (
        createNewImage,
        attachImageToTPage,
        createNewHWPage,
        uploadTestPage,
        is_sid_used,
        doesHWHaveIDPage,
        getMissingDNMPages,
        uploadHWPage,
        uploadUnknownPage,
        uploadCollidingPage,
        updateDNMGroup,
        updateIDGroup,
        buildUpToDateAnnotation,
        updateQGroup,
        updateGroupAfterChange,
        checkTestScanned,
        updateTestAfterChange,
        getSIDFromTest,
        sidToTest,
        replaceMissingHWQuestion,
        replaceMissingTestPage,
        removeAllScannedPages,
        get_groups_using_image,
        removeScannedTestPage,
        removeScannedHWPage,
        removeScannedEXPage,
        listBundles,
        getImagesInBundle,
        getBundleFromImage,
        getPageFromBundle,
        updateImageRotation,
    )

    from plom.db.db_manage import (
        getUnknownPages,
        getDiscardedPages,
        getCollidingPageNames,
        getTPageImage,
        getHWPageImage,
        getEXPageImage,
        getAllTestImages,
        getQuestionImages,
        testOwnersLoggedIn,
        moveUnknownToExtraPage,
        moveUnknownToHWPage,
        moveUnknownToTPage,
        checkTPage,
        removeUnknownImage,
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
        RgetNotAutoIdentified,
        RgetProgress,
        RgetMarkHistogram,
        RgetQuestionUserProgress,
        RgetCompletionStatus,
        RgetOutToDo,
        RgetStatus,
        RgetSpreadsheet,
        RgetOriginalFiles,
        RgetCoverPageInfo,
        RgetMarkReview,
        RgetIDReview,
        RgetUserFullProgress,
        RgetDanglingPages,
        RgetFilesInTest,
        RgetFilesInAllTests,
    )

    from plom.db.db_identify import (
        IDcountAll,
        IDcountIdentified,
        IDgetIdentifiedTests,
        IDgetUnidentifiedTests,
        IDgetNextTask,
        IDgiveTaskToClient,
        IDgetDoneTasks,
        IDgetImage,
        ID_get_donotmark_images,
        IDgetImagesOfUnidentified,
        ID_id_paper,
        IDgetImageFromATest,
        IDreviewID,
        ID_get_predictions,
    )

    from plom.db.db_mark import (
        McountAll,
        McountMarked,
        MgetDoneTasks,
        MgetNextTask,
        MgiveTaskToClient,
        MtakeTaskFromClient,
        Mget_annotations,
        MgetOneImageFilename,
        MgetWholePaper,
        MreviewQuestion,
        MrevertTask,
        MgetAllTags,
        McheckTagKeyExists,
        McheckTagTextExists,
        McreateNewTag,
        MgetTagsOfTask,
        MaddExistingTag,
        MremoveExistingTag,
        MgetOneImageRotation,
    )

    from plom.db.db_rubric import (
        McreateRubric,
        MgetRubrics,
        MmodifyRubric,
        Rget_test_rubric_count_matrix,
        Rget_rubric_counts,
        Rget_rubric_details,
    )
