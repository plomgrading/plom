# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.http import HttpResponse, HttpRequest, Http404
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from django.contrib import messages
from plom.plom_exceptions import PlomDependencyConflict

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from plom_server.Papers.models import Specification


class SpecSummaryView(ManagerRequiredView):
    """Display a read-only summary of the test specification in the browser."""

    def get(self, request: HttpRequest) -> HttpResponse:
        if SpecificationService.is_there_a_spec():
            context = {
                "spec": SpecificationService.get_the_spec(),
            }
        else:
            context = {"spec": None}
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


class HTMXDeleteSpec(ManagerRequiredView):
    def delete(self, request):
        try:
            SpecificationService.remove_spec()
            return HttpResponseClientRefresh()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))
