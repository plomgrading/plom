# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023, 2025-2026 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import base64

from django.urls import reverse
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Base.base_group_views import ManagerRequiredView
from ..services import PrenameSettingService, ExamMockerService


class PrenamingConfigView(ManagerRequiredView):
    """Configure and mock prenaming settings."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        version = 1
        try:
            prenaming_config = PrenameSettingService.get_prenaming_config()
            png_bytes = ExamMockerService.mock_ID_page(
                version, prenaming_config["xcoord"], prenaming_config["ycoord"]
            )
            png_as_string = base64.b64encode(png_bytes).decode("ascii")

            context.update(
                {
                    "prename_config": prenaming_config,
                    "mock_id_image": png_as_string,
                }
            )
            return render(request, "Preparation/prenaming_configuration.html", context)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return redirect(reverse("prep_conflict"))

    def post(self, request: HttpRequest) -> HttpResponse:
        success_url = "configure_prenaming"

        if "set_config" in request.POST:
            # be careful with data coming back from requests - almost always is converted to float.
            # this caused #4053
            try:
                x_pos = float(request.POST.get("xPos"))
                y_pos = float(request.POST.get("yPos"))
            except (ValueError, TypeError) as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))

            try:
                PrenameSettingService.set_prenaming_coords(x_pos, y_pos)
                return redirect(reverse(success_url))
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))
        elif "reset_config" in request.POST:
            try:
                PrenameSettingService.reset_prenaming_coords()
                return redirect(reverse(success_url))
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))
