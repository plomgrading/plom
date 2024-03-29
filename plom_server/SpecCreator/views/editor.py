# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Dict, Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from rest_framework.exceptions import ValidationError

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from ..services import SpecificationUploadService


class SpecEditorView(ManagerRequiredView):
    """Create and modify a test specification in the browser.

    Serves a TOML editor on GET and modifies the test spec
    with unsafe methods.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Serves the TOML editor template."""
        context = self.build_context()
        context.update({"is_there_a_spec": SpecificationService.is_there_a_spec()})
        return render(request, "SpecCreator/launch-page.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Create or replace the test specification using a TOML sent from the browser."""
        context: Dict[str, Any] = {
            "success": False,
            "msg": "Not able to accept that specification",
            "error_list": [],
        }
        data = request.POST
        spec = data.get("spec")
        if not spec:
            context["error_list"] = ["No spec provided"]
            return render(request, "SpecCreator/validation.html", context)
        only_validate = data.get("which_action") == "validate"
        try:
            service = SpecificationUploadService(toml_string=spec)
            if only_validate:
                service.validate_spec()
                context["msg"] = "Specification passes validity checks."
            else:
                service.save_spec()
                context["msg"] = "Specification saved!"
            context["success"] = True
        except (ValueError, RuntimeError) as e:
            context["error_list"] = [str(e)]
        except ValidationError as errs:
            for k, v in errs.detail.items():
                if isinstance(v, list) and len(v) == 1:
                    context["error_list"].append(f"{k}: {v[0]}")
                    continue
                if k == "question" and isinstance(v, dict):
                    # this big ol pile of spaghetti renders errors within questions
                    for j, u in v.items():
                        if isinstance(u, dict):
                            for i, w in u.items():
                                if isinstance(w, list) and len(w) == 1:
                                    (w,) = w
                                context["error_list"].append(f"{k} {j}: {i}: {w}")
                        else:
                            context["error_list"].append(f"{k} {j}: {u}")
                    continue
                # last ditch effort if neither of the above: make 'em into strings
                context["error_list"].append(f"{k}: {str(v)}")
        return render(request, "SpecCreator/validation.html", context)
