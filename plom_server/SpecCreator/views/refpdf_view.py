# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import re

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.utils.text import slugify
from django_htmx.http import HttpResponseClientRefresh

from Preparation.services import TestSourceService, PQVMappingService

from . import TestSpecPageView
from ..services import StagingSpecificationService, ReferencePDFService
from ..forms import TestSpecVersionsRefPDFForm


class TestSpecCreatorVersionsRefPDFPage(TestSpecPageView):
    """Upload a reference PDF for rendering page thumbnails."""

    def build_form(self):
        ref = ReferencePDFService()

        try:
            pdf = ref.get_pdf().pdf
            files = {"pdf": pdf}
        except RuntimeError:
            files = {}

        return TestSpecVersionsRefPDFForm(files=files)

    def build_context(self):
        spec = StagingSpecificationService()
        ref = ReferencePDFService()
        context = super().build_context("upload")
        context.update({"refpdf_uploaded": ref.is_there_a_reference_pdf()})
        if ref.is_there_a_reference_pdf():
            context.update({"n_pages": spec.get_n_pages()})
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "SpecCreator/upload-pdf.html", context)

    def delete(self, request):
        spec = StagingSpecificationService()
        ref = ReferencePDFService()
        ref.delete_pdf()
        spec.clear_questions()
        spec.clear_pages()

        return HttpResponseClientRefresh()

    def post(self, request):
        context = self.build_context()
        form = TestSpecVersionsRefPDFForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data

            n_pages = data["num_pages"]
            slug = slugify(re.sub(".pdf$", "", str(data["pdf"])))

            spec = StagingSpecificationService()
            ref = ReferencePDFService()

            # if the number of pages has changed, and there are
            # test sources or a QV map present, delete them
            if n_pages != spec.get_n_pages():
                tss = TestSourceService()
                tss.delete_all_test_sources()
                pqv = PQVMappingService()
                pqv.remove_pqv_map()

            ref.new_pdf(spec, slug, n_pages, request.FILES["pdf"])

            return HttpResponseRedirect(reverse("id_page"))
        else:
            context.update({"form": form})
            return render(request, "SpecCreator/upload-pdf.html", context)
