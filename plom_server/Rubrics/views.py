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

    template_name = "Rubrics/rubrics_landing.html"
    rs = RubricService()
    rubric_filter_form = RubricFilterForm

    def get(self, request):
        context = self.build_context()

        filter_form = self.rubric_filter_form(request.GET)
        rubrics = self.rs.get_all_rubrics()

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

        return render(request, self.template_name, context=context)


class RubricItemView(ManagerRequiredView):
    """A page for displaying a single rubric and its annotations."""

    template_name = "Rubrics/rubric_item.html"
    rs = RubricService()
    form = RubricEditForm

    def get(self, request, rubric_key):
        context = self.build_context()

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)
        rubric = self.rs.get_all_rubrics().get(key=rubric_key)
        annotations = self.rs.get_annotation_from_rubric(rubric)
        rubric_as_html = self.rs.get_rubric_as_html(rubric)
        context.update(
            {
                "rubric": rubric,
                "form": self.form(instance=rubric),
                "annotations": annotations,
                "rubric_as_html": rubric_as_html,
            }
        )

        return render(request, self.template_name, context=context)

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

    template_name = "Rubrics/annotation_item.html"
    rs = RubricService()

    def get(self, request, annotation_key):
        context = self.build_context()

        annotation = self.rs.get_all_annotations().get(pk=annotation_key)
        rubrics = self.rs.get_rubrics_from_annotation(annotation)
        context.update({"annotation": annotation, "rubrics": rubrics})

        return render(request, self.template_name, context=context)
