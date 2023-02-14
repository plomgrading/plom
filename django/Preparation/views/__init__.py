# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates

from .home import (
    PreparationLandingView,
    LandingResetSpec,
    LandingResetSources,
    LandingPrenameToggle,
    LandingResetClasslist,
    LandingResetQVmap,
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
from .classic_server import ClassicServerInfoView, ClassicServerURLView
from .mocker import MockExamView
from .create_papers import PaperCreationView
from .misc_extras import MiscExtrasView, ExtraPageView
