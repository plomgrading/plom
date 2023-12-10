# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Any, Dict

from django.shortcuts import render
from django.urls import reverse
from django.http import HttpRequest, HttpResponse

from django_htmx.http import HttpResponseClientRedirect

from rest_framework.serializers import ValidationError


from Base.base_group_views import ManagerRequiredView

from ..services import TemplateSolnSpecService
from Papers.services import SolnSpecService


class SolnSpecView(ManagerRequiredView):
    def get(self, request):
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
        SolnSpecService.remove_soln_spec()
        return HttpResponseClientRedirect(reverse("soln_spec"))

    def patch(self, request: HttpRequest) -> HttpResponse:
        spec = TemplateSolnSpecService().build_soln_toml_from_test_spec()

        context: Dict[str, Any] = {
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

        context: Dict[str, Any] = {
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
                context[
                    "unused_pages"
                ] = SolnSpecService.get_unused_pages_in_toml_string(spec)
            except ValueError as e:
                context["error_list"].append(f"{e}")
            except ValidationError as errs:
                for k, v in errs.detail.items():
                    if k == "solution" and isinstance(v, dict):
                        for j, u in v.items():
                            context["error_list"].append(f"solution {j}: {u}")
                    else:
                        context["error_list"].append(f"{k}: {v}")

        if action == "submit" and context["valid"]:
            return HttpResponseClientRedirect(reverse("soln_spec"))
        else:
            return render(request, "Finish/soln_spec.html", context=context)


class TemplateSolnSpecView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        soln_toml = TemplateSolnSpecService().build_template_soln_toml()
        context.update(
            {
                "soln_toml": soln_toml,
                "toml_line_by_line": soln_toml.split("\n"),
            }
        )
        return render(request, "Finish/template_soln_spec.html", context=context)
