# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from django.shortcuts import render, redirect

from Base.base_group_views import ManagerRequiredView
from Rubrics.services import RubricService
from Rubrics.forms import RubricForm


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    template_name = "Rubrics/rubrics_landing.html"
    rs = RubricService()

    def get(self, request):
        context = self.build_context()

        value_counts = self.rs.rubric_counts("value")  # dict of values
        self.rs.plot_hist_dict(value_counts, "value_histogram")  # histogram from dict

        display_delta_counts = self.rs.rubric_counts("display_delta")
        self.rs.plot_hist_dict(display_delta_counts, "delta_histogram")

        form = RubricForm()
        context.update({"form": form})

        return render(request, self.template_name, context=context)

    def select(request):
        """Feedback form using boolean checkboxes."""

        options = []
        if request.method == "POST":
            if "option1" in request.POST:
                options.append("option1")

            if "option2" in request.POST:
                options.append("option2")

            if "option3" in request.POST:
                options.append("option3")

        request.session["options"] = options
        return redirect("rubrics_landing")
