# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from .server_info import (
    UserRole,
    ExamInfo,
    ServerVersion,
    ServerInfo,
    CloseUser,
    ObtainAuthTokenUpdateLastLogin,
)

from .spec_handler import SpecificationHandler

from .identify import (
    GetClasslist,
    GetIDPredictions,
    IDgetDoneTasks,
    IDgetNextTask,
    IDprogressCount,
    IDclaimThisTask,
    IDdirect,
)

from .mark import (
    QuestionMaxMark,
    MarkingProgress,
    MgetPageDataQuestionInContext,
    MgetOneImage,
    MgetAnnotations,
    MgetAnnotationImage,
    GetTasks,
    ReassignTask,
    ResetTask,
    TagsFromCodeView,
    GetAllTags,
    GetSolutionImage,
)

from .scan import (
    ScanListBundles,
    ScanBundleActions,
    ScanMapBundle,
)

from .finish import (
    FinishReassembled,
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
    MgetRubricMarkingTasks,
)

from .latex import (
    MlatexFragment,
)

from .mark_question import QuestionMarkingViewSet
