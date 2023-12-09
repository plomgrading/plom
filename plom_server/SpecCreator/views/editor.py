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
                context["msg"] = "Tests passed: specification appears to be valid"
            else:
                service.save_spec()
                context["msg"] = "Specification saved!"
            context["success"] = True
        except ValidationError as e:
            errlist = []
            for k, v in e.detail.items():
                if isinstance(v, list) and len(v) == 1:
                    errstr = f"{k}: {v[0]}"
                    errlist.append(errstr)
                    continue
                if isinstance(v, dict):
                    # this big ol pile of spaghetti renders errors within questions
                    for kk, vv in v.items():
                        if isinstance(vv, dict):
                            for kkk, vvv in vv.items():
                                if isinstance(vvv, list) and len(vvv) == 1:
                                    errstr = f"{k}: {kk}: {kkk}: {vvv[0]}"
                                else:
                                    errstr = f"{k}: {kk}: {kkk}: {str(vvv)}"
                                errlist.append(errstr)
                        else:
                            errstr = f"{k}: {kk}: {vv}"
                            errlist.append(errstr)
                    continue
                # last ditch effort if neither of the above: make 'em into strings
                errstr = f"{k}: {str(v)}"
                errlist.append(errstr)
            context["error_list"] = errlist
        except (ValueError, RuntimeError) as e:
            context["error_list"] = [str(e)]
        return render(request, "SpecCreator/validation.html", context)
