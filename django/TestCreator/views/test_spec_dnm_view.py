import re
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TestCreator.views import TestSpecPDFView

from ..services import TestSpecService
from .. import forms


class TestSpecCreatorDNMPage(TestSpecPDFView):
    """Select do-not-mark pages."""

    def build_form(self):
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecPDFSelectForm(n_pages)
        return form

    def build_context(self):
        context = super().build_context("dnm_page")
        spec = TestSpecService()
        context.update(
            {
                "num_questions": spec.get_n_questions(),
                "x_data": spec.get_dnm_page_alpine_xdata(),
                "pages": spec.get_pages_for_dnm_select_page(),
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
        return render(request, "TestCreator/test-spec-do-not-mark-page.html", context)

    def post(self, request):
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecPDFSelectForm(n_pages, request.POST)
        if form.is_valid():
            data = form.cleaned_data

            dnm_idx = []
            for key, value in data.items():
                if "page" in key and value == True:
                    idx = int(re.sub("\D", "", key))
                    dnm_idx.append(idx)
            spec.set_do_not_mark_pages(dnm_idx)

            # set the do not mark page's completion status
            the_spec = spec.specification()
            the_spec.dnm_page_submitted = True
            the_spec.save()

            spec.unvalidate()

            return HttpResponseRedirect(reverse("validate"))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(
                request, "TestCreator/test-spec-do-not-mark-page.html", context
            )
