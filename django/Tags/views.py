# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.shortcuts import render, redirect

from Base.base_group_views import ManagerRequiredView
from Tags.forms import TagFormFilter
from Tags.services.tag_service import TagService


class TagLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing papers by tag."""

    template_name = "Tags/tags_landing.html"
    ts = TagService()

    def get(self, request):
        context = self.build_context()

        text_field_form = TagFormFilter()
        context.update({"text_field_form": text_field_form})
        context.update({"text_entry1": request.session["text_entry1"]})

        print(request.session["text_entry1"])

        if request.session["strict_match"] == "on":
            print("exact match")
            rubrics = self.ts.get_rubrics_with_tag_exact(request.session["text_entry1"])
        else:
            print("loose match")
            rubrics = self.ts.get_rubrics_with_tag(request.session["text_entry1"])

        print(rubrics.__len__())
        # print(list(rubrics))

        context.update({"tag_count": rubrics.__len__()})
        context.update({"rubrics": rubrics})

        return render(request, self.template_name, context=context)

    def tag_filter(request):
        """Filter papers by tag."""
        request.session["text_entry1"] = ""
        request.session["strict_match"] = ""

        if request.method == "POST":
            print("POST: ", request.POST)
            request.session["text_entry1"] = request.POST["text_entry1"]
            request.session["strict_match"] = request.POST.get("strict_match", "")

        return redirect("tags_landing")