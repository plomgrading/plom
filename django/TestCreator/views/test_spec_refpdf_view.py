import re
from django.urls import reverse
from django.utils.text import slugify
from . import BaseTestSpecFormView
from .. import services
from .. import forms
from .. import models


class TestSpecCreatorVersionsRefPDFPage(BaseTestSpecFormView):
    template_name = 'TestCreator/test-spec-upload-pdf.html'
    form_class = forms.TestSpecVersionsRefPDFForm
    slug = None

    def get_context_data(self, **kwargs):
        return super().get_context_data('upload', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['versions'] = services.get_num_versions()
        initial['num_to_produce'] = services.get_num_to_produce()
        return initial

    def form_valid(self, form):
        # TODO: if the uploaded PDF has the same number of pages, don't force reset everything, give an option
        form_data = form.cleaned_data

        self.num_pages = form_data['num_pages']
        self.slug = slugify(re.sub('.pdf$', '', str(form_data['pdf'])))

        # make sure there's only one PDF saved in the database at one time
        saved_pdfs = models.ReferencePDF.objects.all()
        if len(saved_pdfs) > 0:
            saved_pdfs.delete()

        pdf = services.create_pdf(self.slug, self.num_pages, self.request.FILES['pdf'])
        services.get_and_save_pdf_images(pdf)
        services.set_pages(pdf)
        
        # when we upload a new PDF, clear questions
        services.clear_questions()

        # update the progress
        services.progress_set_versions_pdf(True)
        services.progress_set_id_page(False)
        services.progress_set_question_page(False)
        services.progress_set_dnm_page(False)
        services.progress_clear_questions()
        services.progress_set_validate_page(False)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('id_page')
