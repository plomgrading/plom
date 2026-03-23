# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from .progress_landing import ProgressLandingView, ToolsLandingView

from .progress_identify import (
    ProgressAllIdentifyTasks,
    IDImageView,
    ClearID,
    IDImageWrapView,
)

from .progress_mark import (
    ProgressMarkHome,
    ProgressMarkStatsView,
    ProgressMarkDetailsView,
    ProgressMarkVersionCompareView,
    ProgressMarkStartMarking,
)

from .progress_task_annot import (
    ProgressMarkingTaskFilterView,
    ProgressMarkingTaskDetailsView,
    ProgressNewestMarkingTaskDetailsView,
    AnnotationImageWrapView,
    AnnotationImageView,
    OriginalImageWrapView,
    AllTaskOverviewView,
    MarkingTaskTagView,
    MarkingTaskResetView,
    MarkingTaskReassignView,
)

from .progress_markerinfo import (
    ProgressMarkerInfoHome,
)
