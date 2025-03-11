# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2025 Aden Chan

from .student_marks_service import StudentMarkService
from .ta_marking_service import TaMarkingService
from .annotation_data_service import AnnotationDataService
from .reassemble_service import ReassembleService
from .data_extraction_service import DataExtractionService
from .matplotlib_service import MatplotlibService
from .d3_service import D3Service

from .build_soln_service import BuildSolutionService
from .soln_images import SolnImageService
from .soln_source import SolnSourceService
from .template_soln_spec import TemplateSolnSpecService
from .build_student_report_service import BuildStudentReportService
from .ReportPDFService import GRAPH_DETAILS
