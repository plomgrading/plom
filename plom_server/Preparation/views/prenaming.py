# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages

from Base.base_group_views import ManagerRequiredView

from Preparation.services import PrenameSettingService
from plom.plom_exceptions import PlomDependencyConflict


class PrenamingView(ManagerRequiredView):
    def post(self, request):
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(True)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

    def delete(self, request):
        pss = PrenameSettingService()
        try:
            pss.set_prenaming_setting(False)
            return HttpResponseClientRedirect(reverse("prep_classlist"))
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))
