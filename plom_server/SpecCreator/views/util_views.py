# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import render
from django.urls import reverse

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from Papers.models import Specification

from ..services import SpecificationUploadService
from . import TestSpecPageView


class TestSpecResetView(ManagerRequiredView):
    def post(self, request):
        SpecificationService.remove_spec()
        return HttpResponseRedirect(reverse("names"))


class TestSpecSubmitView(TestSpecPageView):
    """Prompt the user to confirm the test specification before submitting it to the database."""

    def build_context(self):
        context = super().build_context()
        spec = Specification.load()

        context.update(
            {
                "num_pages": SpecificationService.get_n_pages(),
                "num_versions": SpecificationService.get_n_versions(),
                "num_questions": SpecificationService.get_n_questions(),
                "id_page": spec.idPage,
                "dnm_pages": str(spec.doNotMarkPages),
                "total_marks": SpecificationService.get_total_marks(),
            }
        )

        questions = []
        for q in spec.get_question_list():
            question = {}
            question.update(
                {
                    "pages": q.pages,
                    "label": q.label,
                    "mark": q.mark,
                    "shuffle": q.select,
                }
            )
            questions.append(question)
        context.update({"questions": questions})

        return context


class TestSpecSummaryView(TestSpecSubmitView):
    """View the test spec summary from the preparation landing page."""

    def dispatch(self, request):
        """Don't redirect if the Papers database is populated."""
        return ManagerRequiredView.dispatch(self, request)

    def get(self, request):
        context = self.build_context()

        return render(request, "SpecCreator/summary-page.html", context)


class TestSpecLaunchView(TestSpecPageView):
    """Landing page for the test spec creator."""

    def get(self, request):
        context = self.build_context()
        return render(request, "SpecCreator/launch-page.html", context)

    def post(self, request):
        data = request.POST
        if "spec" in data.keys():
            spec = data["spec"]
            service = SpecificationUploadService(toml_string=spec)
            service.save_spec()
        return render(request, "SpecCreator/validation.html", {})
