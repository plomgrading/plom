# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.shortcuts import render
from django.http import FileResponse, StreamingHttpResponse
from django.urls import reverse
from django.utils.text import slugify

from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from ..services import BuildSolutionService


class BuildSolutionsView(ManagerRequiredView):
    def get(self, request):
        # Note: uses the symbolic constants defined in HueyTaskTracker
        bss = BuildSolutionService()
        context = self.build_context()
        all_paper_status = bss.get_all_paper_status_for_solution_build()

        # Compute some counts required for the page
        n_papers = sum([1 for x in all_paper_status if x["scanned"]])
        n_ready = sum(
            [
                1
                for x in all_paper_status
                if x["scanned"] and x["build_soln_status"] != "Complete"
            ]
        )
        n_outdated = sum([1 for x in all_paper_status if x["outdated"]])
        n_queued = sum(
            [
                1
                for x in all_paper_status
                if x["build_soln_status"] in ("Starting", "Queued", "Running")
            ]
        )  # for display purposes started === queued
        n_errors = sum(
            [1 for x in all_paper_status if x["build_soln_status"] == "Error"]
        )
        n_complete = sum(
            [1 for x in all_paper_status if x["build_soln_status"] == "Complete"]
        )

        context.update(
            {
                "papers": all_paper_status,
                "n_papers": n_papers,
                "n_ready": n_ready,
                "n_outdated": n_outdated,
                "n_errors": n_errors,
                "n_complete": n_complete,
                "n_queued": n_queued,
            }
        )
        return render(request, "Finish/build_soln.html", context=context)


class StartOneBuildSoln(ManagerRequiredView):
    def post(self, request, paper_number):
        BuildSolutionService().queue_single_solution_build(paper_number)
        return HttpResponseClientRedirect(reverse("build_soln"))

    def delete(self, request, paper_number):
        BuildSolutionService().reset_single_solution_build(paper_number)
        return HttpResponseClientRedirect(reverse("build_soln"))

    def get(self, request, paper_number):
        return FileResponse(
            BuildSolutionService().get_single_solution_pdf_file(paper_number)
        )

    def put(self, request, paper_number):  # called by "re-build_soln"
        BuildSolutionService().reset_single_solution_build(paper_number)
        BuildSolutionService().queue_single_solution_build(paper_number)
        return HttpResponseClientRedirect(reverse("build_soln"))


class StartAllBuildSoln(ManagerRequiredView):
    def post(self, request):
        BuildSolutionService().queue_all_solution_builds()
        return HttpResponseClientRedirect(reverse("build_soln"))

    def delete(self, request):
        BuildSolutionService().reset_all_soln_build()
        return HttpResponseClientRedirect(reverse("build_soln"))

    def get(self, request):
        # using zipfly python package.  see django example here
        # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
        short_name = slugify(SpecificationService.get_shortname())
        zgen = BuildSolutionService().get_zipfly_generator()
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = (
            f"attachment; filename={short_name}_solutions.zip"
        )
        return response


class CancelQueuedBuildSoln(ManagerRequiredView):
    def delete(self, request):
        BuildSolutionService().try_to_cancel_all_queued_chores()
        return HttpResponseClientRedirect(reverse("build_soln"))
