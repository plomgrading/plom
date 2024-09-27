# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.services import SolnSpecService, SpecificationService
from ..services import SolnSourceService, BuildSolutionService


class SolnHomeView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        all_soln_pdf_present = SolnSourceService().are_all_solution_pdf_present()
        context.update(
            {
                "is_there_a_spec": SpecificationService.is_there_a_spec(),
                "is_there_a_soln_spec": SolnSpecService.is_there_a_soln_spec(),
                "versions": SpecificationService.get_n_versions(),
                "number_of_soln_source_pdfs": SolnSourceService().get_number_of_solution_pdf(),
                "all_soln_pdf_present": all_soln_pdf_present,
            }
        )
        if all_soln_pdf_present:
            bss = BuildSolutionService()
            all_paper_status = bss.get_all_paper_status_for_solution_build()
            n_papers = sum([1 for x in all_paper_status if x["scanned"]])
            n_complete = sum(
                [1 for x in all_paper_status if x["build_soln_status"] == "Complete"]
            )
            context.update({"n_papers": n_papers, "n_complete": n_complete})
        return render(request, "Finish/soln_home.html", context=context)
