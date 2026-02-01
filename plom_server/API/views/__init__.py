# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2026 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025-2026 Aidan Murphy

from .paperstoprint import (
    papersToPrint,
)

from .server_info import (
    UserRole,
    ExamInfo,
    ServerVersion,
    ServerInfo,
    CloseUser,
    ObtainAuthTokenUpdateLastLogin,
)

from .user_info import UsersInfo


from .source_handler import (
    SourceOverview,
    SourceDetail,
)

from .spec_handler import SpecificationAPIView
from .public_code import PublicCodeAPIView
from .classlist import Classlist
from .pqvmap import PQVmap

from .identify import (
    GetClasslist,
    GetIDPredictions,
    IDgetDoneTasks,
    IDgetNextTask,
    IDprogressCount,
    IDclaimOrSubmitTask,
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
    ScanListPapers,
    ScanBundleActions,
    ScanMapBundle,
)

from .finish import (
    FinishReassembled,
    FinishReport,
    FinishSolution,
    FinishUnmarked,
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

from .mark_question import MarkTaskNextAvailable, MarkTask

from .rectangle_extractor import RectangleExtractorView
