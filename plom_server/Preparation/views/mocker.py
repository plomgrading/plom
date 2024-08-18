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

from ..services import PrenameSettingService
from plom.plom_exceptions import PlomDependencyConflict
from django.shortcuts import redirect
from django.contrib import messages


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


# TODO: move view and service from mocker to prenaming,
#   use django form instead of html template
#   get server values and put them as form defaults
class MockPrenameView(ManagerRequiredView):
    """Create a mock exam id page with a prename box."""

    def post(self, request: HttpRequest) -> HttpResponse:
        # guard blank inputs
        x_pos = request.POST.get("xPos")
        x_pos = float(x_pos) if x_pos else None
        y_pos = request.POST.get("yPos")
        y_pos = float(y_pos) if y_pos else None

        if "set_config" in request.POST:
            pss = PrenameSettingService()
            try:
                pss.set_prenaming_coords(x_pos, y_pos)
                return HttpResponse(status=204)
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect("create_paperPDFs")
            PrenameSettingService().set_prenaming_coords(x_pos, y_pos)
            return HttpResponse(status=204)
        # TODO: render the mock on the same page rather than returning a file response
        elif "mock_id" in request.POST:
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
            mock_exam_file = File(
                BytesIO(mock_exam_pdf_bytes), name=f"mock_v{version}.pdf"
            )
            return FileResponse(mock_exam_file, content_type="application/pdf")
