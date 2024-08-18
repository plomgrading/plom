# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from io import BytesIO
from pathlib import Path

from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages

from plom.plom_exceptions import PlomDependencyConflict
from Base.base_group_views import ManagerRequiredView
from ..services import PrenameSettingService, ExamMockerService, SourceService

from django.shortcuts import redirect
from django.http import HttpRequest, HttpResponse, FileResponse
from Papers.services import SpecificationService
from django.core.files import File


class PrenamingView(ManagerRequiredView):
    def post(self, request):
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(True)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

    def delete(self, request):
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(False)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))


# TODO: move view and service from mocker to prenaming,
#   use django form instead of html template
#   get server values and put them as form defaults
class PrenamingConfigView(ManagerRequiredView):
    """Configure and mock prenaming settings."""

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
