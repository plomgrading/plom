# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Julian Lapenna

import datetime as dt

from django.shortcuts import render
from django.http import HttpResponse

from Base.base_group_views import ManagerRequiredView
from .services.report_download_service import ReportDownloadService
from Papers.models import Specification


class ReportLandingPageView(ManagerRequiredView):
    """Page for downloading different reports."""

    template_name = "Reports/reports_landing.html"

    def get(self, request):
        context = self.build_context()

        return render(request, self.template_name, context=context)

    def report_download(request):
        rds = ReportDownloadService()
        spec = Specification.load().spec_dict
        filename = (
            "Report-"
            + spec["name"]
            + "--"
            + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S+00-00")
        )

        report_bytes = rds.get_report_bytes(versions=True)
        response = HttpResponse(report_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={filename}.pdf"

        return response
