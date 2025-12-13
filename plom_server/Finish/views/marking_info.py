# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Aden Chan

import arrow

from django.http import HttpRequest, HttpResponse

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import StudentMarkService, TaMarkingService, AnnotationDataService


class MarksDownloadView(ManagerRequiredView):
    """View to download marks."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Download marks as a csv file."""
        version_info = request.POST.get("version_info", "off") == "on"
        timing_info = request.POST.get("timing_info", "off") == "on"
        warning_info = request.POST.get("warning_info", "off") == "on"
        privacy_mode = request.POST.get("privacy_mode", "off") == "on"
        privacy_salt = request.POST.get("privacy_mode_salt", "")
        csv_as_string = StudentMarkService.build_marks_csv_as_string(
            version_info,
            timing_info,
            warning_info,
            privacy_mode=privacy_mode,
            privacy_salt=privacy_salt,
        )

        filename = (
            "marks--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response


class TAInfoDownloadView(ManagerRequiredView):
    """View to download TA info."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Download TA marking information as a csv file."""
        tms = TaMarkingService()
        csv_as_string = tms.build_ta_info_csv_as_string()

        filename = (
            "TA--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response


class AnnotationsInfoDownloadView(ManagerRequiredView):
    """View to download Annotation info."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Download annotation information as a csv file."""
        ads = AnnotationDataService()
        csv_as_string = ads.get_csv_data_as_string()

        filename = (
            "annotations--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response
