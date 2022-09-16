import toml
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import render
from django.urls import reverse

from Base.base_group_views import ManagerRequiredView
from Papers.services import TestSpecificationService

from SpecCreator.views import TestSpecPageView

from ..services import (
    StagingSpecificationService,
    TestSpecService,
    ReferencePDFService,
    TestSpecProgressService,
    TestSpecGenerateService,
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
    """Clear the test specification from the preparation landing page"""

    def post(self, request):
        spec = StagingSpecificationService()
        ref_service = ReferencePDFService()
        spec.clear_questions()
        ref_service.delete_pdf()
        spec.reset_specification()
        return HttpResponseRedirect(reverse("prep_landing"))


class TestSpecViewRefPDF(ManagerRequiredView):
    """Return the reference PDF in a file response"""
    def get(self, request):
        ref = ReferencePDFService()
        pdf_file = ref.get_pdf().pdf
        pdf_doc = SimpleUploadedFile('spec_reference.pdf', pdf_file.open('rb').read(), content_type="application/pdf")
        return FileResponse(pdf_doc)


class TestSpecGenTomlView(ManagerRequiredView):
    def dispatch(self, request, **kwargs):
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)
        if not prog.is_everything_complete():
            raise PermissionDenied("Specification not completed yet.")

        return super().dispatch(request, **kwargs)

    def get(self, request):
        spec = TestSpecService()
        gen = TestSpecGenerateService(spec)
        spec_dict = gen.generate_spec_dict()
        toml_file = toml.dumps(spec_dict)

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

        return render(request, "SpecCreator/test-spec-download-page.html", context)


class TestSpecSubmitView(TestSpecPageView):
    """Prompt the user to confirm the test specification before submitting it to the database"""

    def build_context(self):
        context = super().build_context("submit")
        spec = StagingSpecificationService()
        pages = spec.get_page_list()
        n_questions = spec.get_n_questions()

        context.update({
            "num_pages": len(pages),
            "num_versions": spec.get_n_versions(),
            "num_questions": n_questions,
            "id_page": spec.get_id_page_number(),
            "dnm_pages": ", ".join(f"p. {i}" for i in spec.get_dnm_page_numbers()),
            "total_marks": spec.get_total_marks()
        })

        questions = []
        for i in range(n_questions):
            one_index = i + 1
            question = {}
            question.update({
                "pages": ", ".join(f"p. {j}" for j in spec.get_question_pages(one_index)),
            })
            if spec.has_question(one_index):
                q_dict = spec.get_question(one_index)
                question.update({
                    "label": q_dict['label'],
                    "mark": q_dict['mark'],
                    "shuffle": q_dict['select'],
                })
            else:
                question.update({
                    "label": "",
                    "mark": "",
                    "shuffle": "",
                })
            questions.append(question)
        context.update({"questions": questions})

        return context

    def get(self, request):
        spec = StagingSpecificationService()
        if not spec.is_valid():
            raise PermissionDenied("Specification not completed yet.")

        context = self.build_context()

        return render(request, "SpecCreator/test-spec-submit-page.html", context)

    def post(self, request):
        staging_spec = StagingSpecificationService()
        spec_dict = staging_spec.get_staging_spec_dict()

        spec = TestSpecificationService()
        spec.store_validated_spec(spec_dict)

        return HttpResponseRedirect(reverse('download'))


class TestSpecSummaryView(TestSpecSubmitView):
    """View the test spec summary and return to the creator page"""

    def get(self, request):
        spec = StagingSpecificationService()
        if not spec.is_valid():
            raise PermissionDenied("Specification not completed yet.")

        context = self.build_context()

        return render(request, "SpecCreator/test-spec-summary-page.html", context)


class TestSpecLaunchView(TestSpecPageView):
    """Landing page for the test spec creator."""

    def get(self, request):
        context = self.build_context("launch")
        return render(request, "SpecCreator/test-spec-launch-page.html", context)
