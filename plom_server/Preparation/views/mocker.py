# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2026 Aidan Murphy

from io import BytesIO

from django.http import HttpRequest, HttpResponse, FileResponse
from django.core.files import File

from plom_server.Base.base_group_views import ManagerRequiredView

from ..services import ExamMockerService


class MockExamView(ManagerRequiredView):
    """Create a mock test PDF."""

    def get(self, request: HttpRequest, *, version: int) -> HttpResponse:
        mock_exam_pdf_bytes = ExamMockerService.mock_exam(version)
        mock_exam_file = File(BytesIO(mock_exam_pdf_bytes), name=f"mock_v{version}.pdf")
        return FileResponse(mock_exam_file, content_type="application/pdf")
