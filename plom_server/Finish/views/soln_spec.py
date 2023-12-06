# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from ..services import TemplateSolnSpecService, SolnSpecService


class SolnSpecView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        context.update(
            {"is_there_a_soln_spec": SolnSpecService().is_there_a_soln_spec()}
        )
        return render(request, "Finish/soln_spec.html", context=context)


class TemplateSolnSpecView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        soln_toml = TemplateSolnSpecService().build_template_soln_toml()
        context.update(
            {
                "generated_toml": soln_toml,
                "toml_line_by_line": soln_toml.split("\n"),
            }
        )
        return render(request, "Finish/template_soln_spec.html", context=context)
