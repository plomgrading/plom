import re
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.utils.text import slugify
from django_htmx.http import HttpResponseClientRefresh

from TestCreator.views import TestSpecPageView
from ..services import TestSpecService, ReferencePDFService
from .. import forms
from .. import models


class TestSpecCreatorVersionsRefPDFPage(TestSpecPageView):
    """Upload a reference PDF for rendering page thumbnails"""

    def build_form(self):
        spec = TestSpecService()
        ref = ReferencePDFService(spec)

        try:
            pdf = ref.get_pdf().pdf
            files = {"pdf": pdf}
        except RuntimeError:
            files = {}

        return forms.TestSpecVersionsRefPDFForm(files=files)

    def build_context(self):
        spec = TestSpecService()
        ref = ReferencePDFService(spec)
        context = super().build_context("upload")
        context.update({"refpdf_uploaded": ref.is_there_a_reference_pdf()})
        if ref.is_there_a_reference_pdf():
            context.update({"n_pages": spec.get_n_pages()})
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "TestCreator/test-spec-upload-pdf.html", context)

    def delete(self, request):
        spec = TestSpecService()
        ref = ReferencePDFService(spec)
        ref.delete_pdf()
        spec.clear_questions()

        the_spec = spec.specification()
        the_spec.pages = {}
        the_spec.save()

        return HttpResponseClientRefresh()

    def post(self, request):
        context = self.build_context()
        form = forms.TestSpecVersionsRefPDFForm(request.POST, request.FILES)
        print(form.files)
        if form.is_valid():
            data = form.cleaned_data

            n_pages = data["num_pages"]
            slug = slugify(re.sub(".pdf$", "", str(data["pdf"])))

            spec = TestSpecService()
            ref = ReferencePDFService(spec)
            ref.new_pdf(slug, n_pages, request.FILES["pdf"])

            # set do not mark page as incomplete
            the_spec = spec.specification()
            the_spec.dnm_page_submitted = False
            the_spec.save()

            spec.unvalidate()

            return HttpResponseRedirect(reverse("id_page"))
        else:
            context.update({"form": form})
            return render(request, "TestCreator/test-spec-upload-pdf.html", context)
