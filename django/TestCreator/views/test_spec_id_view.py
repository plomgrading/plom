import re
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TestCreator.views import TestSpecPDFView

from ..services import TestSpecService
from .. import forms


class TestSpecCreatorIDPage(TestSpecPDFView):
    """Select the ID page of the test."""

    def build_form(self):
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecIDPageForm(n_pages)
        return form

    def build_context(self):
        context = super().build_context("id_page")
        spec = TestSpecService()

        context.update(
            {
                "x_data": spec.get_id_page_alpine_xdata(),
                "pages": spec.get_pages_for_id_select_page(),
            }
        )

        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "TestCreator/test-spec-id-page.html", context)

    def post(self, request):
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecIDPageForm(n_pages, request.POST)
        if form.is_valid():
            data = form.cleaned_data
            spec.clear_id_page()
            for key, value in data.items():
                if "page" in key and value == True:
                    idx = int(re.sub("\D", "", key))
                    spec.set_id_page(idx)

            spec.unvalidate()

            return HttpResponseRedirect(reverse("questions"))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(request, "TestCreator/test-spec-id-page.html", context)
