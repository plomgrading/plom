# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from .marking_info import (
    MarkingInformationPaperView,
    MarkingInformationView,
)
from .reassembly import (
    ReassemblePapersView,
    StartOneReassembly,
    StartAllReassembly,
    CancelQueuedReassembly,
    DownloadRangeOfReassembled,
)
from .build_soln_pdf import (
    BuildSolutionsView,
    CancelQueuedBuildSoln,
    StartAllBuildSoln,
    StartOneBuildSoln,
)
from .soln_home import SolnHomeView
from .soln_spec import SolnSpecView, TemplateSolnSpecView
from .soln_sources import SolnSourcesView

from .student_report import StudentReportView
