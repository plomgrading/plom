# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from typing import Dict, Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from Papers.services import SpecificationService

from . import SpecBaseView


class SpecEditorTextArea(SpecBaseView):
    """A text editor component for the test specification."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Serves the text editor with a TOML default text if there's already a spec."""
        spec_exists = SpecificationService.is_there_a_spec()
        context: Dict[str, Any] = {"is_there_a_spec": spec_exists}
        if spec_exists:
            context.update(
                {
                    "spec_toml": SpecificationService.get_the_spec_as_toml(),
                }
            )

        return render(request, "SpecCreator/toml-editor.html", context)
