# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework import serializers

# from django.http import HttpResponseBadRequest

from plom.plom_exceptions import PlomDependencyConflict
from django_htmx.http import HttpResponseClientRedirect

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService

from ..services import SpecificationUploadService


class SpecEditorView(ManagerRequiredView):
    """Create and modify a test specification in the browser.

    Serves a TOML editor on GET and modifies the test spec
    with unsafe methods.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Serves the TOML editor template."""
        context = self.build_context()
        context.update({"editable_toml": ""})
        context.update({"is_there_a_spec": SpecificationService.is_there_a_spec()})
        if SpecificationService.is_there_a_spec():
            context.update(
                {
                    "editable_toml": SpecificationService.get_the_spec_as_toml(),
                }
            )
        return render(request, "SpecCreator/launch-page.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Create or replace the test specification using a TOML sent from the browser.

        Caution: HTMX calls this, and from multiple views, to insert a
        little blob of validation output, and (on success) to push the
        spec.
        """
        context = self.build_context()
        context.update(
            {
                "success": False,
                "msg": "Not able to accept that specification",
                "error_list": [],
            }
        )
        data = request.POST
        gave_toml_file = data.get("which_action") == "upload_file"
        if gave_toml_file:
            f = request.FILES.get("toml_file")
            if not f:
                # TODO: I still don't understand HTMX error handling: this silently fails
                # TODO: to see this, change the name="toml_file" to something else in the html
                # return HttpResponseBadRequest("No toml file provided")
                context["error_list"] = ["No toml file provided"]
                return render(request, "SpecCreator/validation.html", context)
            d = f.file.getvalue()
            try:
                spec = d.decode()
            except UnicodeDecodeError as e:
                context["error_list"] = [
                    f"Only utf-8 encoded toml files are accepted: {str(e)}"
                ]
                return render(request, "SpecCreator/validation.html", context)
        else:
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
                # Spec saved successfully - redirect to the summary page.
                return HttpResponseClientRedirect(reverse("spec_summary"))

            context["success"] = True
        except PlomDependencyConflict as e:
            context["error_list"] = [f"Dependency error - {e}"]
        except PermissionDenied as e:
            context["error_list"] = [str(e)]
        except (ValueError, RuntimeError) as e:
            context["error_list"] = [f"Cannot modify specification - {e}"]
        except serializers.ValidationError as errs:
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
