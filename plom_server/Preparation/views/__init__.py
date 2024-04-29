# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from .home import (
    PreparationLandingView,
    LandingResetSpec,
    LandingResetSources,
    LandingPrenameToggle,
    LandingResetClasslist,
    LandingResetQVmap,
    LandingFinishedToggle,
)
from .source_manage import SourceManageView, SourceReadOnlyView, ReferenceImageView
from .prenaming import PrenamingView
from .classlist_manage import (
    ClasslistView,
    ClasslistDownloadView,
    ClasslistReadOnlyView,
)
from .pqv_mapping import (
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
)
from .mocker import MockExamView
from .create_papers import PaperCreationView
from .misc_extras import MiscExtrasView, ExtraPageView, ScrapPaperView
