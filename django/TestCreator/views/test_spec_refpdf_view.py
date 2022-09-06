import re
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.utils.text import slugify

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

    def get(self, request):
        context = self.build_context("upload")
        context.update({
            "form": self.build_form()
        })
        return render(request, 'TestCreator/test-spec-upload-pdf.html', context)

    def post(self, request):
        context = self.build_context("upload")
        form = forms.TestSpecVersionsRefPDFForm(request.POST, request.FILES)
        print(form.files)
        if form.is_valid():
            data = form.cleaned_data

            n_pages = data["num_pages"]
            slug = slugify(re.sub('.pdf$', '', str(data['pdf'])))

            spec = TestSpecService()
            ref = ReferencePDFService(spec)
            ref.new_pdf(slug, n_pages, request.FILES['pdf'])

            # set do not mark page as incomplete
            the_spec = spec.specification()
            the_spec.dnm_page_submitted = False
            the_spec.save()

            spec.unvalidate()

            return HttpResponseRedirect(reverse('id_page'))
        else:
            context.update({'form': form})
            return render(request, 'TestCreator/test-spec-upload-pdf.html', context)
