# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import re

from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from . import TestSpecPDFView
from ..services import StagingSpecificationService, SpecCreatorFrontendService
from ..forms import SpecQuestionDetailsForm


class TestSpecCreatorQuestionDetailPage(TestSpecPDFView):
    """Select pages, max mark, and shuffle status for a question."""

    def build_form(self, question_id):
        spec = StagingSpecificationService()
        initial = {}
        if spec.has_question(question_id):
            question = spec.get_question(question_id)
            initial.update(
                {
                    "label": question["label"],
                    "mark": question["mark"],
                    "shuffle": "S" if question["select"] == "shuffle" else "F",
                }
            )
        else:
            initial.update({"label": f"Q{question_id}"})
            if spec.get_n_versions() > 1:
                initial.update({"shuffle": "S"})
            else:
                initial.update({"shuffle": "F"})

        n_pages = spec.get_n_pages()
        form = SpecQuestionDetailsForm(n_pages, initial=initial, q_idx=question_id)
        return form

    def build_context(self, question_id):
        context = super().build_context(f"question_{question_id}")
        spec = StagingSpecificationService()
        page_list = spec.get_page_list()
        frontend = SpecCreatorFrontendService()

        context.update(
            {
                "question_id": question_id,
                "prev_id": question_id - 1,
                "total_marks": spec.get_total_marks(),
                "n_versions": spec.get_n_versions(),
                "n_questions": spec.get_n_questions(),
                "x_data": frontend.get_question_detail_page_alpine_xdata(
                    page_list, question_id
                ),
                "pages": frontend.get_pages_for_question_detail_page(
                    page_list, question_id
                ),
            }
        )

        if spec.has_question(question_id):
            context.update(
                {
                    "assigned_to_others": spec.get_marks_assigned_to_other_questions(
                        question_id
                    )
                }
            )
        else:
            context.update({"assigned_to_others": 0})

        return context

    def get(self, request, q_idx):
        context = self.build_context(q_idx)
        context.update(
            {
                "form": self.build_form(q_idx),
            }
        )
        return render(request, "SpecCreator/question-detail-page.html", context)

    def post(self, request, q_idx):
        spec = StagingSpecificationService()
        n_pages = spec.get_n_pages()
        form = SpecQuestionDetailsForm(n_pages, request.POST, q_idx=q_idx)

        if form.is_valid():
            data = form.cleaned_data
            label = data["label"]
            mark = data["mark"]
            shuffle = data["shuffle"] == "S"

            question_ids = []
            for key, value in data.items():
                if "page" in key and value is True:
                    idx = int(re.sub(r"\D", "", key))
                    question_ids.append(idx + 1)
            spec.create_or_replace_question(q_idx, label, mark, shuffle, question_ids)

            return HttpResponseRedirect(self.get_success_url(q_idx))
        else:
            context = self.build_context(q_idx)
            context.update({"form": form})
            return render(request, "SpecCreator/question-detail-page.html", context)

    def get_success_url(self, q_idx):
        spec = StagingSpecificationService()
        n_questions = spec.get_n_questions()
        if q_idx == n_questions:
            return reverse("dnm_page")
        else:
            return reverse("q_detail", args=(q_idx + 1,))
