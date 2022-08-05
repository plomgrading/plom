import re
from django.urls import reverse
from . import BaseTestSpecFormPDFView
from .. import forms
from .. import services

class TestSpecCreatorDNMPage(BaseTestSpecFormPDFView):
    template_name = 'TestCreator/test-spec-do-not-mark-page.html'
    form_class = forms.TestSpecPDFSelectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('dnm_page', **kwargs)
        context['num_questions'] = services.get_num_questions()
        context['x_data'] = services.get_dnm_page_alpine_xdata()
        context['pages'] = services.get_pages_for_dnm_select_page()
        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        # save do not mark pages
        dnm_idx = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                dnm_idx.append(idx)
        services.set_do_not_mark_pages(dnm_idx)

        services.progress_set_dnm_page(True)


        return super().form_valid(form)

    def get_success_url(self):
        return reverse('validate')