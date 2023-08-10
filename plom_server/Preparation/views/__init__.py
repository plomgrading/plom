# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from .home import (
    PreparationLandingView,
    LandingResetSpec,
    LandingResetSources,
    LandingPrenameToggle,
    LandingResetClasslist,
    LandingResetQVmap,
    LandingFinishedToggle,
)
from .test_source_manage import TestSourceManageView
from .prenaming import PrenamingView
from .classlist_manage import (
    ClasslistView,
    ClasslistDownloadView,
    ClasslistDeleteView,
    ClasslistReadOnlyView,
)
from .pqv_mapping import (
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
    PQVMappingReadOnlyView,
)
from .mocker import MockExamView
from .create_papers import PaperCreationView
from .misc_extras import MiscExtrasView, ExtraPageView
