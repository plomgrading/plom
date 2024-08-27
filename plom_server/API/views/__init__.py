# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from .server_info import (
    UserRole,
    ExamInfo,
    GetSpecification,
    ServerVersion,
    ServerInfo,
    CloseUser,
    ObtainAuthTokenUpdateLastLogin,
)

from .identify import (
    GetClasslist,
    GetIDPredictions,
    IDgetDoneTasks,
    IDgetNextTask,
    IDprogressCount,
    IDclaimThisTask,
)

from .mark import (
    QuestionMaxMark,
    MarkingProgress,
    MgetPageDataQuestionInContext,
    MgetOneImage,
    MgetAnnotations,
    MgetAnnotationImage,
    GetTasks,
    TagsFromCodeView,
    GetAllTags,
    GetSolutionImage,
)

from .report import (
    REPspreadsheet,
    REPidentified,
    REPcompletionStatus,
    REPcoverPageInfo,
)

from .rubrics import (
    MgetAllRubrics,
    MgetRubricsByQuestion,
    MgetRubricPanes,
    McreateRubric,
    MmodifyRubric,
    MgetRubricUsages,
)

from .latex import (
    MlatexFragment,
)

from .mark_question import QuestionMarkingViewSet
