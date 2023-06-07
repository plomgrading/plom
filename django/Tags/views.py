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
        print("GET: ", request.GET)
        print("session: ", request.session)
        context = self.build_context()
        tag_filter_text = request.session.get("tag_filter_text", "")
        tag_filter_strict = request.session.get("strict_match", "off")

        text_field_form = TagFormFilter()
        context.update({"text_field_form": text_field_form})
        context.update({"tag_filter_text": tag_filter_text})


        if tag_filter_strict == "on":
            print("exact match")
            task_tags = self.ts.get_task_tags_with_tag_exact(tag_filter_text)
        else:
            print("loose match")
            task_tags = self.ts.get_task_tags_with_tag(tag_filter_text)

        print(task_tags)
        print(task_tags.__len__())

        print(task_tags[0].text)
        print(task_tags[0].task.all())
        papers = self.ts.get_papers_from_task_tags(task_tags)
        print(papers)
        print(type(papers))

        context.update({"tag_count": task_tags.__len__()})
        context.update({"task_tags": task_tags})
        context.update({"papers": papers})

        return render(request, self.template_name, context=context)

    def tag_filter(request):
        """Filter papers by tag."""
        print("POST:", request.POST)
        request.session["tag_filter_text"] = request.POST.get("tag_filter_text", "")
        request.session["strict_match"] = request.POST.get("strict_match", "off")

        return redirect("tags_landing")
