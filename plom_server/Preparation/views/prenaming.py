# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from plom.plom_exceptions import PlomDependencyConflict
from Base.base_group_views import ManagerRequiredView
from ..services import PrenameSettingService
from ..models import PrenamingSetting


class PrenamingView(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(True)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

    def delete(self, request: HttpRequest) -> HttpResponse:
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(False)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))


class PrenamingConfigView(ManagerRequiredView):
    """Configure and mock prenaming settings."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        context.update(
            {
                "prename_config": PrenameSettingService().get_prenaming_config(),
            }
        )
        return render(request, "Preparation/prenaming_configuration.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        success_url = "configure_prenaming"
        ps_meta = PrenamingSetting._meta
        pss = PrenameSettingService()
        # guard inputs
        x_pos = request.POST.get("xPos")
        x_pos = float(x_pos) if x_pos else ps_meta.get_field("xcoord").get_default()
        y_pos = request.POST.get("yPos")
        y_pos = float(y_pos) if y_pos else ps_meta.get_field("ycoord").get_default()

        if "set_config" in request.POST:
            try:
                pss.set_prenaming_coords(x_pos, y_pos)
                return redirect(reverse(success_url))
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))
        elif "reset_config" in request.POST:
            try:
                pss.reset_prenaming_coords()
                return redirect(reverse(success_url))
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))
