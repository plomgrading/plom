# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from .marking_info import (
    MarkingInformationPaperView,
    MarkingInformationView,
)
from .reassembly import (
    ReassemblePapersView,
    StartOneReassembly,
    StartAllReassembly,
    CancelQueuedReassembly,
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
