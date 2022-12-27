# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from .server_info import (
    GetSpecification,
    ServerVersion,
    CloseUser,
)

from .identify import (
    GetClasslist,
    GetIDPredictions,
    IDgetDoneTasks,
    IDgetNextTask,
    IDprogressCount,
    IDclaimThisTask,
    IDgetImage,
)

from .mark import (
    QuestionMaxMark_how_to_get_data,
    QuestionMaxMark,
    MgetNextTask,
    MclaimThisTask,
    MgetQuestionPageData,
    MgetOneImage,
    MgetAnnotations,
    MgetAnnotationImage,
)
