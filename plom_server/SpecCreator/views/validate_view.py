# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from . import TestSpecPageView
from ..services import StagingSpecificationService
from ..forms import SpecValidateForm


class TestSpecValidateView(TestSpecPageView):
    """Validate the test specification."""

    def build_context(self):
        context = super().build_context("validate")
        spec = StagingSpecificationService()
        n_questions = spec.get_n_questions()
        n_pages = spec.get_n_pages()

        context.update(
            {
                "num_pages": n_pages,
                "num_versions": spec.get_n_versions(),
                "id_page": spec.get_id_page_number(),
                "dnm_pages": ", ".join(f"p. {i}" for i in spec.get_dnm_page_numbers()),
                "total_marks": spec.get_total_marks(),
            }
        )

        questions = []
        for i in range(n_questions):
            one_index = i + 1
            question = {}
            question.update(
                {
                    "pages": ", ".join(
                        f"p. {j}" for j in spec.get_question_pages(one_index)
                    ),
                }
            )
            if spec.has_question(one_index):
                q_dict = spec.get_question(one_index)
                question.update(
                    {
                        "label": q_dict["label"],
                        "mark": q_dict["mark"],
                        "shuffle": q_dict["select"],
                    }
                )
            else:
                question.update(
                    {
                        "label": "",
                        "mark": "",
                        "shuffle": "",
                    }
                )
            questions.append(question)
        context.update({"questions": questions})
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": SpecValidateForm()})
        return render(request, "SpecCreator/validate-page.html", context)

    def post(self, request):
        form = SpecValidateForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect(reverse("spec_submit"))
        else:
            context = self.build_context()
            context.update(
                {
                    "form": form,
                }
            )
            return render(request, "SpecCreator/validate-page.html", context)
