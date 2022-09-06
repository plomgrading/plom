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

            return HttpResponseRedirect(reverse('id_page'))
        else:
            context.update({'form': form})
            return render(request, 'TestCreator/test-spec-upload-pdf.html', context)

# class TestSpecCreatorVersionsRefPDFPage(BaseTestSpecFormView):
#     template_name = 'TestCreator/test-spec-upload-pdf.html'
#     form_class = forms.TestSpecVersionsRefPDFForm
#     slug = None

#     def get_context_data(self, **kwargs):
#         return super().get_context_data('upload', **kwargs)

#     def get_initial(self):
#         initial = super().get_initial()
#         spec = TestSpecService()
#         initial['versions'] = spec.get_n_versions()
#         initial['num_to_produce'] = spec.get_n_to_produce()
#         return initial

#     def form_valid(self, form):
#         # TODO: if the uploaded PDF has the same number of pages, don't force reset everything, give an option
#         form_data = form.cleaned_data

#         self.num_pages = form_data['num_pages']
#         self.slug = slugify(re.sub('.pdf$', '', str(form_data['pdf'])))

#         spec = TestSpecService()
#         ref_service = ReferencePDFService(spec)
#         ref_service.new_pdf(self.slug, self.num_pages, self.request.FILES['pdf'])

#         # set do not mark page
#         the_spec = spec.specification()
#         the_spec.dnm_page_submitted = False
#         the_spec.save()

#         return super().form_valid(form)

#     def get_success_url(self):
#         return reverse('id_page')
