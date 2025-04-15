# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from io import BytesIO
from pathlib import Path

from django.http import HttpRequest, HttpResponse, FileResponse
from django.core.files import File

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService

from ..services import ExamMockerService, SourceService


class MockExamView(ManagerRequiredView):
    """Create a mock test PDF."""

    def post(self, request: HttpRequest, *, version: int) -> HttpResponse:
        mocker = ExamMockerService()
        source_path = Path(SourceService._get_source_file(version).path)

        mock_exam_pdf_bytes = mocker.mock_exam(version, source_path)
        mock_exam_file = File(BytesIO(mock_exam_pdf_bytes), name=f"mock_v{version}.pdf")
        return FileResponse(mock_exam_file, content_type="application/pdf")
