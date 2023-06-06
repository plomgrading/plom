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

        value_counts = self.rs.rubric_counts("value")  # dict of values
        self.rs.plot_hist_dict(value_counts, "value_histogram")  # histogram from dict

        display_delta_counts = self.rs.rubric_counts("display_delta")
        self.rs.plot_hist_dict(display_delta_counts, "delta_histogram")

        form = RubricForm()
        context.update({"form": form})

        rubrics = Rubric.objects.all()
        print(rubrics)
        print('rubrics[119]:', rubrics[119])
        print()
        print('annotations: ', rubrics[119].annotations.all())
        anns = self.rs.get_annotation_from_rubric(rubrics[119])
        print(anns)
        print("now get rubrics from annotation:")
        print(self.rs.get_rubrics_from_annotation(anns[0]))
        print()
        print()
        print("now get rubrics from paper 62:")
        print(self.rs.get_rubrics_from_paper(62))
        print()
        print("rubrics marked by manager:")
        print(self.rs.get_rubrics_from_user("manager"))  

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
