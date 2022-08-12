import re
from django.urls import reverse
from . import BaseTestSpecFormPDFView
from ..services import TestSpecService
from .. import forms

class TestSpecCreatorDNMPage(BaseTestSpecFormPDFView):
    template_name = 'TestCreator/test-spec-do-not-mark-page.html'
    form_class = forms.TestSpecPDFSelectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('dnm_page', **kwargs)
        spec = TestSpecService()
        context['num_questions'] = spec.get_n_questions()
        context['x_data'] = spec.get_dnm_page_alpine_xdata()
        context['pages'] = spec.get_pages_for_dnm_select_page()
        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        # save do not mark pages
        spec = TestSpecService()
        dnm_idx = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                dnm_idx.append(idx)
        spec.set_do_not_mark_pages(dnm_idx)
        
        # set do not mark page
        the_spec = spec.specification()
        the_spec.dnm_page_submitted = True
        the_spec.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('validate')