# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from django.shortcuts import render, redirect

from Base.base_group_views import ManagerRequiredView
from Rubrics.services import RubricService
from Rubrics.forms import RubricForm
from Rubrics.models import Rubric


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    template_name = "Rubrics/rubrics_landing.html"
    rs = RubricService()

    def get(self, request):
        context = self.build_context()


        return render(request, self.template_name, context=context)
