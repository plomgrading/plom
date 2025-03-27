# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from plom_server.Base.base_group_views import ManagerRequiredView
from .forms import TagFormFilter, TagEditForm
from .services import TagService


class TagLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing papers by tag."""

    def get(self, request):
        template_name = "Tags/tags_landing.html"
        ts = TagService()

        context = self.build_context()
        text_field_form = TagFormFilter()

        tag_filter_text = request.session.get("tag_filter_text", "")
        tag_filter_strict = request.session.get("strict_match", "off")

        text_field_form.fields["tag_filter_text"].initial = tag_filter_text
        text_field_form.fields["strict_match"].initial = False
        if tag_filter_strict == "on":
            text_field_form.fields["strict_match"].initial = True

        if tag_filter_strict == "on":
            task_tags = ts.get_task_tags_with_tag_exact(tag_filter_text)
        else:
            task_tags = ts.get_task_tags_with_tag(tag_filter_text)

        papers = ts.get_papers_from_task_tags(task_tags)
        tag_counts = ts.get_task_tags_counts()

        context.update(
            {
                "tag_count": task_tags.__len__(),
                "task_tags": task_tags,
                "papers": papers,
                "tag_counts": tag_counts,
                "text_field_form": text_field_form,
                "tag_filter_text": tag_filter_text,
                "tag_filter_strict": tag_filter_strict,
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def tag_filter(request):
        """Filter papers by tag."""
        request.session["tag_filter_text"] = request.POST.get("tag_filter_text", "")
        request.session["strict_match"] = request.POST.get("strict_match", "off")

        return redirect("tags_landing")


class TagItemView(ManagerRequiredView):
    """A page for displaying a single tag and related information."""

    def get(self, request, tag_id):
        template_name = "Tags/tag_item.html"
        ts = TagService()
        form = TagEditForm

        context = self.build_context()

        tag = ts.get_tag_from_id(tag_id=tag_id)
        context.update({"tag": tag, "form": form(instance=tag)})

        return render(request, template_name, context=context)

    @staticmethod
    def post(request: HttpRequest, *, tag_id: int) -> HttpResponse:
        form = TagEditForm(request.POST)
        if not form.is_valid():
            # TODO for now we just do nothing and let it redirect (?)
            pass
        tag = TagService().get_tag_from_id(tag_id=tag_id)
        TagService().update_tag_content(tag=tag, content=form.cleaned_data)
        return redirect("tag_item", tag_id=tag_id)

    @staticmethod
    def tag_delete(request, tag_id):
        """Delete a tag."""
        TagService().delete_tag(tag_id=tag_id)
        return redirect("tags_landing")
