# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024, 2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from plom_server.Base.base_group_views import (
    LeadMarkerOrManagerView,
    IdentifierOrManagerView,
)


class ProgressLandingView(LeadMarkerOrManagerView):
    """Page displaying a menu of different 'Marking' progress views."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "Progress/progress_landing.html")


class ToolsLandingView(LeadMarkerOrManagerView):
    """Page giving an overview of various misc tools."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "Progress/tools_landing.html")


class ProgressIdentifyHome(IdentifierOrManagerView):
    """Page displaying a menu of different 'Identifying' progress views."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "Progress/Identify/identify_home.html")
