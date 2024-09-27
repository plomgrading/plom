# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import render
from django.http import HttpResponse

from Base.base_group_views import ManagerRequiredView
from Finish.services import ReportPDFService, StudentMarkService, GRAPH_DETAILS
from Mark.services import MarkingTaskService
from Papers.services import SpecificationService


class ReportLandingPageView(ManagerRequiredView):
    """Page for downloading different reports."""

    template_name = "Reports/reports_landing.html"

    def get(self, request):
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        total_tasks = MarkingTaskService().get_n_valid_tasks()
        all_marked = StudentMarkService().are_all_papers_marked() and total_tasks > 0

        context.update(
            {
                "all_marked": all_marked,
                "graph_list": [
                    {"name": key, **value} for key, value in GRAPH_DETAILS.items()
                ],
            }
        )

        return render(request, self.template_name, context=context)

    @staticmethod
    def report_download(request):
        # Get the selected report type from the form
        report_type = request.POST.get("report_type", "brief")

        # Get the selected graphs for the brief report
        selected_graphs = {
            key: request.POST.get(key) == "on" for key in GRAPH_DETAILS.keys()
        }

        try:
            # Generate the report based on the selected type and graphs
            if report_type == "full":
                d = ReportPDFService.pdf_builder(versions=True, brief=False)
            else:
                d = ReportPDFService.pdf_builder(
                    versions=True, brief=True, selected_graphs=selected_graphs
                )
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
