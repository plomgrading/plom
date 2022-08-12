from re import TEMPLATE
from django.urls import reverse
from . import BaseTestSpecFormView
from ..services import TestSpecService
from .. import forms

class TestSpecCreatorNamesPage(BaseTestSpecFormView):
    template_name = 'TestCreator/test-spec-names-page.html'
    form_class = forms.TestSpecNamesForm

    def get_context_data(self, **kwargs):
        return super().get_context_data('names', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        spec = TestSpecService()
        initial['long_name'] = spec.get_long_name()
        initial['short_name'] = spec.get_short_name()

        versions = spec.get_n_versions()
        if versions:
            initial['versions'] = versions
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        spec = TestSpecService()

        long_name = form_data['long_name']
        spec.set_long_name(long_name)

        short_name = form_data['short_name']
        spec.set_short_name(short_name)

        n_versions = form_data['versions']
        spec.set_n_versions(n_versions)
        if n_versions == 1:
            spec.fix_all_questions()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('upload')