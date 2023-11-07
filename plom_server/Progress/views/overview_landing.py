# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
from django.shortcuts import render

from Base.base_group_views import LeadMarkerOrManagerView


class OverviewLandingView(LeadMarkerOrManagerView):
    def get(self, request):
        return render(request, "Progress/overview_landing.html")
