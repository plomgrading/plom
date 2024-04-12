# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald

from pathlib import Path
import shutil

from django.http import HttpRequest, HttpResponse, FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from ..services import ExamMockerService, SourceService


class MockExamView(ManagerRequiredView):
    """Create a mock test PDF."""

    def post(self, request: HttpRequest, *, version: int) -> HttpResponse:
        mocker = ExamMockerService()
        source_path = Path(SourceService._get_source_file(version).path)

        n_pages = SpecificationService.get_n_pages()
        pdf_path = mocker.mock_exam(
            version, source_path, n_pages, SpecificationService.get_short_name_slug()
        )
        pdf_doc = SimpleUploadedFile(
            pdf_path.name, pdf_path.open("rb").read(), content_type="application/pdf"
        )
        shutil.rmtree(pdf_path.parent)
        return FileResponse(pdf_doc)
