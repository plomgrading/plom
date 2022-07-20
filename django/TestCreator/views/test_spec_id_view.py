import re
from django.urls import reverse
from . import BaseTestSpecFormPDFView
from .. import services
from .. import forms

class TestSpecCreatorIDPage(BaseTestSpecFormPDFView):
    template_name = 'test_creator/test-spec-id-page.html'
    form_class = forms.TestSpecIDPageForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('id_page', **kwargs)
        
        context['x_data'] = services.get_id_page_alpine_xdata()
        context['pages'] = services.get_pages_for_id_select_page()

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        for field in form_data:
            print(f'{field}: {form_data[field]}')

        # save ID page
        services.clear_id_page()
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                services.set_id_page(idx)

        services.progress_set_id_page(True)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('questions')