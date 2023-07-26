# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView

from ..services import PrenameSettingService


class PrenamingView(ManagerRequiredView):
    def get(self, request):
        pss = PrenameSettingService()
        context = self.build_context()
        context.update({"prenaming_enabled": pss.get_prenaming_setting()})
        return render(request, "Preparation/prenaming_manage.html", context)

    def post(self, request):
        pss = PrenameSettingService()
        pss.set_prenaming_setting(True)
        return HttpResponseClientRedirect(reverse("prep_prename"))

    def delete(self, request):
        pss = PrenameSettingService()
        pss.set_prenaming_setting(False)
        return HttpResponseClientRedirect(reverse("prep_prename"))
