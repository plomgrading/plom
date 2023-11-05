# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald

import datetime as dt

from django.shortcuts import render
from django.http import HttpResponse

from Base.base_group_views import ManagerRequiredView
from .services.report_download_service import ReportDownloadService
from Papers.services import SpecificationService


class ReportLandingPageView(ManagerRequiredView):
    """Page for downloading different reports."""

    template_name = "Reports/reports_landing.html"

    def get(self, request):
        context = self.build_context()

        return render(request, self.template_name, context=context)

    def report_download(request):
        rds = ReportDownloadService()
        filename = (
            "Report-"
            + SpecificationService.get_shortname()
            + "--"
            + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S+00-00")
        )

        try:
            report_bytes = rds.get_report_bytes(versions=True)
        except ValueError as e:
            response = HttpResponse(
                "Error building report: it is possible marking is incomplete?\n"
                f"Error msg: {e}",
                content_type="text/plain",
            )
            return response
        response = HttpResponse(report_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={filename}.pdf"

        return response
