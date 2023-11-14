# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from Papers.services import SpecificationService

from ..services import SpecificationUploadService
from . import SpecBaseView


class SpecEditorView(SpecBaseView):
    """Create and modify a test specification in the browser.

    Serves a TOML editor on GET and modifies the test spec
    with unsafe methods.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Serves the TOML editor template."""
        context = self.build_context()
        context.update({"is_there_a_spec": SpecificationService.is_there_a_spec()})
        return render(request, "SpecCreator/launch-page.html", context)

    def post(self, request) -> HttpResponse:
        """Create or replace the test specification using a TOML sent from the browser."""
        context = {"success": False}
        data = request.POST
        if "spec" in data.keys():
            spec = data["spec"]

            try:
                service = SpecificationUploadService(toml_string=spec)
                service.save_spec()
                context["success"] = True
            except (ValueError, RuntimeError) as e:
                context.update({"error": str(e)})
        return render(request, "SpecCreator/validation.html", context)
