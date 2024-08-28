# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aidan Murphy

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


class MockPrenamedIDView(ManagerRequiredView):
    """Create a mock png of a prenamed ID page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        x_pos = request.GET.get("xcoord")
        x_pos = float(x_pos) if x_pos else None
        y_pos = request.GET.get("ycoord")
        y_pos = float(y_pos) if y_pos else None
        version = 1

        ems = ExamMockerService()
        mock_exam_png_bytes = ems.mock_ID_page(
            version,
            xcoord=x_pos,
            ycoord=y_pos,
        )
        mock_exam_image = BytesIO(mock_exam_png_bytes)
        return HttpResponse(mock_exam_image, content_type="image/png")
