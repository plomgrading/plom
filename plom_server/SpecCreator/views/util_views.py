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

from . import TestSpecPageView
from ..services import (
    StagingSpecificationService,
    ReferencePDFService,
    SpecificationUploadService,
)


class TestSpecResetView(ManagerRequiredView):
    def post(self, request):
        spec = StagingSpecificationService()
        ref_service = ReferencePDFService()
        spec.clear_questions()
        ref_service.delete_pdf()
        spec.reset_specification()
        return HttpResponseRedirect(reverse("names"))


class TestSpecPrepLandingResetView(ManagerRequiredView):
    """Clear the test specification from the preparation landing page."""

    def post(self, request):
        spec = StagingSpecificationService()
        ref_service = ReferencePDFService()
        spec.clear_questions()
        ref_service.delete_pdf()
        spec.reset_specification()

        SpecificationService.remove_spec()
        return HttpResponseRedirect(reverse("prep_landing"))


class TestSpecViewRefPDF(ManagerRequiredView):
    """Return the reference PDF in a file response."""

    def get(self, request):
        ref = ReferencePDFService()
        pdf_file = ref.get_pdf().pdf
        pdf_doc = SimpleUploadedFile(
            "spec_reference.pdf",
            pdf_file.open("rb").read(),
            content_type="application/pdf",
        )
        return FileResponse(pdf_doc)


class TestSpecGenTomlView(ManagerRequiredView):
    def get(self, request):
        if not SpecificationService.is_there_a_spec():
            raise PermissionDenied("Specification not completed yet.")

        toml_file = SpecificationService.get_the_spec_as_toml()

        response = HttpResponse(toml_file)
        response["mimetype"] = "text/plain"
        response["Content-Disposition"] = "attachment;"
        return response


class TestSpecDownloadView(TestSpecPageView):
    """A page for downloading the test specification as a toml file."""

    def get(self, request):
        spec = StagingSpecificationService()
        if not spec.is_valid():
            return HttpResponseRedirect(reverse("validate"))

        context = self.build_context("download")

        return render(request, "SpecCreator/download-page.html", context)


class TestSpecSubmitView(TestSpecPageView):
    """Prompt the user to confirm the test specification before submitting it to the database."""

    def build_context(self):
        context = super().build_context("submit")
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

    def get(self, request):
        spec = StagingSpecificationService()
        if not spec.is_valid():
            raise PermissionDenied("Specification not completed yet.")

        context = self.build_context()

        return render(request, "SpecCreator/submit-page.html", context)

    def post(self, request):
        staging_spec = StagingSpecificationService()
        spec_dict = staging_spec.get_valid_spec_dict()
        spec_dict.pop(
            "numberToProduce", None
        )  # TODO: numToProduce shouldn't be in here in the first place!

        SpecificationService.store_validated_spec(spec_dict)

        return HttpResponseRedirect(reverse("download"))


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
        context = self.build_context("launch")
        return render(request, "SpecCreator/launch-page.html", context)

    def post(self, request):
        data = request.POST
        if "spec" in data.keys():
            spec = data["spec"]
            service = SpecificationUploadService(toml_string=spec)
            service.save_spec()
        return render(request, "SpecCreator/validation.html", {})
