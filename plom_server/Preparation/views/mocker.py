# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from io import BytesIO
from pathlib import Path

from django.http import HttpRequest, HttpResponse, FileResponse
from django.core.files import File

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from ..services import ExamMockerService, SourceService


class MockExamView(ManagerRequiredView):
    """Create a mock test PDF."""

    def post(self, request: HttpRequest, *, version: int) -> HttpResponse:
        mocker = ExamMockerService()
        source_path = Path(SourceService._get_source_file(version).path)

        n_pages = SpecificationService.get_n_pages()
        mock_exam_pdf_bytes = mocker.mock_exam(
            version, source_path, n_pages, SpecificationService.get_short_name_slug()
        )
        mock_exam_file = File(BytesIO(mock_exam_pdf_bytes), name=f"mock_v{version}.pdf")
        return FileResponse(mock_exam_file, content_type="application/pdf")


class MockPrenameView(ManagerRequiredView):
    """Create a mock exam id page with the prename card."""

    def get(self, request: HttpRequest) -> HttpResponse:
        # guard blank inputs, default vals are WET in html template
        x_pos = request.GET.get("xPos")
        x_pos = float(x_pos) if x_pos else 50.0
        y_pos = request.GET.get("yPos")
        y_pos = float(y_pos) if y_pos else 42.0

        version = 1
        mocker = ExamMockerService()
        source_path = Path(SourceService._get_source_file(version).path)

        id_page_number = SpecificationService.get_id_page_number()
        mock_exam_pdf_bytes = mocker.mock_ID_page(
            version,
            source_path,
            id_page_number,
            SpecificationService.get_short_name_slug(),
            xcoord=x_pos,
            ycoord=y_pos,
        )
        mock_exam_file = File(BytesIO(mock_exam_pdf_bytes), name=f"mock_v{version}.pdf")
        return FileResponse(mock_exam_file, content_type="application/pdf")
