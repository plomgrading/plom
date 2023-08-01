# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import re

from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from . import TestSpecPDFView
from ..services import StagingSpecificationService, SpecCreatorFrontendService
from ..forms import TestSpecPDFSelectForm


class TestSpecCreatorDNMPage(TestSpecPDFView):
    """Select do-not-mark pages."""

    def build_form(self):
        spec = StagingSpecificationService()
        n_pages = spec.get_n_pages()
        form = TestSpecPDFSelectForm(n_pages)
        return form

    def build_context(self):
        context = super().build_context("dnm_page")
        spec = StagingSpecificationService()
        page_list = spec.get_page_list()
        frontend = SpecCreatorFrontendService()

        context.update(
            {
                "num_questions": spec.get_n_questions(),
                "x_data": frontend.get_dnm_page_alpine_xdata(page_list),
                "pages": frontend.get_pages_for_dnm_select_page(page_list),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        context.update(
            {
                "form": self.build_form(),
            }
        )
        return render(request, "SpecCreator/do-not-mark-page.html", context)

    def post(self, request):
        spec = StagingSpecificationService()
        n_pages = spec.get_n_pages()
        form = TestSpecPDFSelectForm(n_pages, request.POST)
        if form.is_valid():
            data = form.cleaned_data

            dnm_idx = []
            for key, value in data.items():
                if "page" in key and value is True:
                    idx = int(re.sub(r"\D", "", key))
                    dnm_idx.append(idx)
            spec.set_do_not_mark_pages(dnm_idx)

            return HttpResponseRedirect(reverse("validate"))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(request, "SpecCreator/do-not-mark-page.html", context)
