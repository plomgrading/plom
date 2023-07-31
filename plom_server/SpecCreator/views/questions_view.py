# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from Preparation.services import TestSourceService, PQVMappingService

from . import TestSpecPageView
from ..services import StagingSpecificationService
from ..forms import TestSpecQuestionsMarksForm


class TestSpecCreatorQuestionsPage(TestSpecPageView):
    """Set the number of questions and total marks."""

    def build_form(self):
        spec = StagingSpecificationService()
        n_questions = spec.get_n_questions()
        marks = spec.get_total_marks()
        initial = {
            "questions": n_questions if n_questions > 0 else None,
            "total_marks": marks if marks > 0 else None,
        }

        form = TestSpecQuestionsMarksForm(initial=initial)
        return form

    def build_context(self):
        context = super().build_context("questions")
        spec = StagingSpecificationService()
        context.update(
            {
                "prev_n_questions": spec.get_n_questions(),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "SpecCreator/questions-marks-page.html", context)

    def post(self, request):
        form = TestSpecQuestionsMarksForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            spec = StagingSpecificationService()

            prev_questions = spec.get_n_questions()
            n_questions = data["questions"]

            if prev_questions != n_questions:
                spec.clear_questions()
                spec.set_n_questions(n_questions)

                # If there are test sources or a QV map present,
                # clear them
                tss = TestSourceService()
                tss.delete_all_test_sources()
                pqv = PQVMappingService()
                pqv.remove_pqv_map()

            marks = data["total_marks"]
            spec.set_total_marks(marks)

            return HttpResponseRedirect(reverse("q_detail", args=(1,)))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(request, "SpecCreator/questions-marks-page.html", context)
