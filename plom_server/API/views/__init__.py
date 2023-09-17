# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from .server_info import (
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
    QuestionMaxMark_how_to_get_data,
    QuestionMaxMark,
    MarkingProgressCount,
    MgetPageDataQuestionInContext,
    MgetOneImage,
    MgetAnnotations,
    MgetAnnotationImage,
    MgetDoneTasks,
    TagsFromCodeView,
    GetAllTags,
)

from .report import (
    REPspreadsheet,
    REPidentified,
    REPcompletionStatus,
    REPcoverPageInfo,
)

from .rubrics import (
    MgetRubricsByQuestion,
    MgetRubricPanes,
    McreateRubric,
    MmodifyRubric,
)

from .latex import (
    MlatexFragment,
)

from .mark_question import QuestionMarkingViewSet
