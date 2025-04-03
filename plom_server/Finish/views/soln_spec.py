# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from typing import Any

from django.shortcuts import render
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django_htmx.http import HttpResponseClientRedirect
from rest_framework import serializers

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SolnSpecService
from ..services import TemplateSolnSpecService, BuildSolutionService, SolnSourceService


class SolnSpecView(ManagerRequiredView):
    def get(self, request):
        """Display solution specification page."""
        context = self.build_context()
        if SolnSpecService.is_there_a_soln_spec():
            soln_toml = SolnSpecService.get_the_soln_spec_as_toml()
            context.update(
                {
                    "is_there_a_soln_spec": True,
                    "soln_toml": soln_toml,
                    "toml_line_by_line": soln_toml.split("\n"),
                    "unused_pages": SolnSpecService.get_unused_pages(),
                }
            )
        else:
            context.update({"is_there_a_soln_spec": False})

        return render(request, "Finish/soln_spec.html", context=context)

    def delete(self, request):
        """Delete the solution specification.

        Also deletes any uploaded sources and marks any built solution
        pdfs as obsolete.
        """
        # remove any uploaded sources, and make any built soln pdfs obsolete.
        BuildSolutionService().reset_all_soln_build()
        SolnSourceService.remove_all_solution_pdf()
        SolnSpecService.remove_soln_spec()
        return HttpResponseClientRedirect(reverse("soln_spec"))

    def patch(self, request: HttpRequest) -> HttpResponse:
        """Sets solution spec to same format as assessment spec."""
        spec = TemplateSolnSpecService().build_soln_toml_from_test_spec()

        context: dict[str, Any] = {
            "just_submitted": True,
            "action": "validate",
            "is_there_a_soln_spec": False,
            "soln_toml": spec,
            "error_list": [],
            "valid": True,
            "unused_pages": SolnSpecService.get_unused_pages_in_toml_string(spec),
        }
        return render(request, "Finish/soln_spec.html", context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Create or replace the test specification using a TOML sent from the browser."""
        data = request.POST
        spec = data.get("spec")
        action = data.get("which_action", "submit")

        context: dict[str, Any] = {
            "just_submitted": True,
            "action": action,
            "is_there_a_soln_spec": False,
            "soln_toml": spec,
            "error_list": [],
            "valid": False,
            "unused_pages": [],
        }

        if not spec:
            context["error_list"] = ["No spec provided"]
        else:
            # we have a spec, try to validate it (or submit it, which validates it too)
            # The "fun" is massaging any returned errors into a form that we
            # can show to the user.
            try:
                if action == "validate":
                    SolnSpecService.validate_soln_spec_from_toml_string(spec)
                else:
                    SolnSpecService.load_soln_spec_from_toml_string(spec)
                context["valid"] = True
                context["unused_pages"] = (
                    SolnSpecService.get_unused_pages_in_toml_string(spec)
                )
            except ValueError as e:
                context["error_list"].append(f"{e}")
            except serializers.ValidationError as errs:
                for k, v in errs.detail.items():
                    if isinstance(v, list) and len(v) == 1:
                        context["error_list"].append(f"{k}: {v[0]}")
                        continue
                    if k == "solution" and isinstance(v, dict):
                        # this big ol pile of spaghetti renders errors within questions
                        for j, u in v.items():
                            if isinstance(u, dict):
                                for i, w in u.items():
                                    if isinstance(w, list) and len(w) == 1:
                                        (w,) = w
                                    context["error_list"].append(f"{k} {j}: {i}: {w}")
                            else:
                                context["error_list"].append(f"{k} {j}: {u}")
                    else:
                        context["error_list"].append(f"{k}: {v}")

        if action == "submit" and context["valid"]:
            return HttpResponseClientRedirect(reverse("soln_spec"))
        else:
            return render(request, "Finish/soln_spec.html", context=context)


class TemplateSolnSpecView(ManagerRequiredView):
    def get(self, request):
        """Generate and display a template soln spec."""
        context = self.build_context()
        soln_toml = TemplateSolnSpecService().build_template_soln_toml()
        context.update(
            {
                "soln_toml": soln_toml,
                "toml_line_by_line": soln_toml.split("\n"),
            }
        )
        return render(request, "Finish/template_soln_spec.html", context=context)
