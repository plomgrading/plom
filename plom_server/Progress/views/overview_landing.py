# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.shortcuts import render

from Base.base_group_views import LeadMarkerOrManagerView


class OverviewLandingView(LeadMarkerOrManagerView):
    """Page displaying a menu of different progress views."""

    def get(self, request):
        return render(request, "Progress/overview_landing.html")


class ToolsLandingView(LeadMarkerOrManagerView):
    """Page giving an overview of various misc tools."""

    def get(self, request):
        return render(request, "Progress/tools_landing.html")
