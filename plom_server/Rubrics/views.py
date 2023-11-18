# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel

from django.shortcuts import render, redirect

from Base.base_group_views import ManagerRequiredView
from .services import RubricService
from .forms import RubricFilterForm, RubricEditForm


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    def get(self, request):
        template_name = "Rubrics/rubrics_landing.html"
        rs = RubricService()
        rubric_filter_form = RubricFilterForm

        context = self.build_context()

        filter_form = rubric_filter_form(request.GET)
        rubrics = rs.get_all_rubrics()

        if filter_form.is_valid():
            question_filter = filter_form.cleaned_data["question_filter"]
            kind_filter = filter_form.cleaned_data["kind_filter"]

            if question_filter:
                rubrics = rubrics.filter(question=question_filter)

            if kind_filter:
                rubrics = rubrics.filter(kind=kind_filter)

        context.update(
            {
                "rubrics": rubrics,
                "rubric_filter_form": filter_form,
            }
        )

        return render(request, template_name, context=context)


class RubricItemView(ManagerRequiredView):
    """A page for displaying a single rubric and its annotations."""

    def get(self, request, rubric_key):
        template_name = "Rubrics/rubric_item.html"
        rs = RubricService()
        form = RubricEditForm

        context = self.build_context()

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)
        rubric = rs.get_all_rubrics().get(key=rubric_key)
        marking_tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)

        rubric_as_html = rs.get_rubric_as_html(rubric)
        context.update(
            {
                "rubric": rubric,
                "form": form(instance=rubric),
                "marking_tasks": marking_tasks,
                "rubric_as_html": rubric_as_html,
            }
        )

        return render(request, template_name, context=context)

    def post(request, rubric_key):
        form = RubricEditForm(request.POST)

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)

        if form.is_valid():
            rubric = RubricItemView.rs.get_all_rubrics().get(key=rubric_key)
            for key, value in form.cleaned_data.items():
                rubric.__setattr__(key, value)
            rubric.save()
        return redirect("rubric_item", rubric_key=rubric_key)


class AnnotationItemView(ManagerRequiredView):
    """A page for displaying a single annotation."""

    def get(self, request, annotation_key):
        template_name = "Rubrics/annotation_item.html"
        rs = RubricService()

        context = self.build_context()

        annotation = rs.get_all_annotations().get(pk=annotation_key)
        rubrics = rs.get_rubrics_from_annotation(annotation)
        context.update({"annotation": annotation, "rubrics": rubrics})

        return render(request, template_name, context=context)
