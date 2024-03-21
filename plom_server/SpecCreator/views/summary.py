# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.http import HttpResponse, HttpRequest, Http404
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from Papers.models import Specification


class SpecSummaryView(ManagerRequiredView):
    """Display a read-only summary of the test specification in the browser."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "spec": SpecificationService.get_the_spec(),
        }
        return render(request, "SpecCreator/summary-page.html", context)


class HTMXSummaryQuestion(ManagerRequiredView):
    """A table displaying information about a single test specification question."""

    def get(self, request: HttpRequest, *, question_index: int) -> HttpResponse:
        if question_index not in SpecificationService.get_question_indices():
            raise Http404(f"Question index {question_index} does not exist.")

        question = Specification.load().get_question_list()[question_index - 1]
        context = {
            "question_index": question_index,
            "question_label": question.label,
            "max_marks": question.mark,
            "question_select": question.select,
            "page_numbers": question.pages,
        }
        return render(request, "SpecCreator/summary-question.html", context)
