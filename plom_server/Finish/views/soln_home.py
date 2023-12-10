# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.services import SolnSpecService, SpecificationService
from ..services import SolnSourceService


class SolnHomeView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        context.update(
            {
                "is_there_a_spec": SpecificationService.is_there_a_spec(),
                "is_there_a_soln_spec": SolnSpecService.is_there_a_soln_spec(),
                "versions": SpecificationService.get_n_versions(),
                "number_of_soln_source_pdfs": SolnSourceService().get_number_of_solution_pdf(),
                "all_soln_pdf_present": SolnSourceService().are_all_solution_pdf_present(),
            }
        )

        return render(request, "Finish/soln_home.html", context=context)
