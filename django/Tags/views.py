# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView


class TagLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing papers by tag."""

    def get(self, request):
        context = self.build_context()
        return render(request, "Tags/tags_landing.html", context=context)
