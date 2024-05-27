# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, Http404
from django.http import FileResponse, StreamingHttpResponse
from django.urls import reverse
from django.utils.text import slugify

from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from ..services import BuildStudentReportService


class BuildStudentReportView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        # Note: uses the symbolic constants defined in HueyTaskTracker

        if not SpecificationService.is_there_a_spec():
            raise Http404("No spec")
        brs = BuildStudentReportService()
        context = self.build_context()
        all_paper_status = brs.get_all_paper_status_for_report_building()
        # Compute some counts required for the page
        n_papers = sum([1 for x in all_paper_status if x["scanned"]])
        n_not_ready = sum(
            [
                1
                for x in all_paper_status
                if x["scanned"] and not (x["identified"] and x["marked"])
            ]
        )
        n_ready = sum(
            [
                1
                for x in all_paper_status
                if x["identified"]
                and x["marked"]
                and x["build_report_status"] == "To Do"
            ]
        )
        n_outdated = sum([1 for x in all_paper_status if x["outdated"]])
        n_queued = sum(
            [
                1
                for x in all_paper_status
                if x["build_report_status"] in ("Starting", "Queued", "Running")
            ]
        )  # for display purposes started === queued
        n_errors = sum(
            [1 for x in all_paper_status if x["build_report_status"] == "Error"]
        )
        n_complete = sum(
            [1 for x in all_paper_status if x["build_report_status"] == "Complete"]
        )

        context.update(
            {
                "papers": all_paper_status,
                "n_papers": n_papers,
                "n_not_ready": n_not_ready,
                "n_ready": n_ready,
                "n_outdated": n_outdated,
                "n_errors": n_errors,
                "n_complete": n_complete,
                "n_queued": n_queued,
            }
        )
        return render(request, "Finish/build_student_report.html", context=context)


class StartOneBuildReport(ManagerRequiredView):
    def post(self, request, paper_number):
        BuildStudentReportService().queue_single_report(paper_number)
        return HttpResponseClientRedirect(reverse("build_student_report"))

    def delete(self, request, paper_number):
        BuildStudentReportService().reset_single_report(paper_number)
        return HttpResponseClientRedirect(reverse("build_student_report"))

    def get(self, request, paper_number):
        pdf_file = BuildStudentReportService().get_single_student_report(paper_number)
        return FileResponse(pdf_file)

    def put(self, request, paper_number): 
        BuildStudentReportService().reset_single_report(paper_number)
        BuildStudentReportService().queue_single_report(paper_number)
        return HttpResponseClientRedirect(reverse("build_student_report"))


class StartAllBuildReport(ManagerRequiredView):
    def post(self, request):
        BuildStudentReportService().queue_all_report()
        return HttpResponseClientRedirect(reverse("build_student_report"))

    def delete(self, request):
        BuildStudentReportService().reset_all_reports()
        return HttpResponseClientRedirect(reverse("build_student_report"))

    def get(self, request):
        # using zipfly python package.  see django example here
        # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
        short_name = slugify(SpecificationService.get_shortname())
        zgen = BuildStudentReportService().get_zipfly_generator(short_name)
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = (
            f"attachment; filename={short_name}_student_report.zip"
        )
        return response


class CancelQueuedBuildReport(ManagerRequiredView):
    def delete(self, request):
        BuildStudentReportService().try_to_cancel_all_queued_chores()
        return HttpResponseClientRedirect(reverse("build_student_report"))
