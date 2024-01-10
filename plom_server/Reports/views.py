# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.shortcuts import render
from django.http import HttpResponse

from Base.base_group_views import ManagerRequiredView
from Finish.services import ReportPDFService, ReassembleService
from Mark.services import MarkingTaskService


class ReportLandingPageView(ManagerRequiredView):
    """Page for downloading different reports."""

    template_name = "Reports/reports_landing.html"

    def get(self, request):
        context = self.build_context()
        total_tasks = MarkingTaskService().get_n_valid_tasks()
        all_marked = ReassembleService().are_all_papers_marked() and total_tasks > 0
        context.update(
            {
                "all_marked": all_marked,
            }
        )

        return render(request, self.template_name, context=context)

    @staticmethod
    def report_download(request):
        try:
            d = ReportPDFService.pdf_builder(versions=True)
        except ValueError as e:
            response = HttpResponse(
                "Error building report: it is possible marking is incomplete?\n"
                f"Error msg: {e}",
                content_type="text/plain",
            )
            return response
        response = HttpResponse(d["bytes"], content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={d['filename']}"

        return response
