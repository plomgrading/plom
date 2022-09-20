from .home import PreparationLandingView
from .test_source_manage import TestSourceManageView
from .prenaming import PrenamingView
from .classlist_manage import ClasslistView, ClasslistDownloadView, ClasslistDeleteView
from .pqv_mapping import (
    PQVMappingView,
    PQVMappingDownloadView,
    PQVMappingDeleteView,
    PQVMappingUploadView,
)
from .classic_server import ClassicServerInfoView, ClassicServerURLView
from .mocker import MockExamView
from .create_papers import PaperCreationView