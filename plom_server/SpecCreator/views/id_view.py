import re
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from SpecCreator.views import TestSpecPDFView
from SpecCreator.services import StagingSpecificationService, SpecCreatorFrontendService

from .. import forms


class TestSpecCreatorIDPage(TestSpecPDFView):
    """Select the ID page of the test."""

    def build_form(self):
        spec = StagingSpecificationService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecIDPageForm(n_pages)
        return form

    def build_context(self):
        context = super().build_context("id_page")
        spec = StagingSpecificationService()
        page_list = spec.get_page_list()
        frontend = SpecCreatorFrontendService()

        context.update(
            {
                "x_data": frontend.get_id_page_alpine_xdata(page_list),
                "pages": frontend.get_pages_for_id_select_page(page_list),
            }
        )

        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "SpecCreator/id-page.html", context)

    def post(self, request):
        spec = StagingSpecificationService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecIDPageForm(n_pages, request.POST)
        if form.is_valid():
            data = form.cleaned_data
            spec.clear_id_page()
            for key, value in data.items():
                if "page" in key and value is True:
                    idx = int(re.sub(r"\D", "", key))
                    spec.set_id_page(idx)

            return HttpResponseRedirect(reverse("questions"))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(request, "SpecCreator/id-page.html", context)
