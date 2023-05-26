# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    def get(self, request):
        context = self.build_context()
        return render(request, "Rubrics/rubrics_landing.html", context=context)
