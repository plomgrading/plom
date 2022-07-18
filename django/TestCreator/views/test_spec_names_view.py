from django.urls import reverse
from . import BaseTestSpecFormView
from .. import services
from .. import forms

class TestSpecCreatorNamesPage(BaseTestSpecFormView):
    template_name = 'test_creator/test-spec-names-page.html'
    form_class = forms.TestSpecNamesForm

    def get_context_data(self, **kwargs):
        return super().get_context_data('names', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['long_name'] = services.get_long_name()
        initial['short_name'] = services.get_short_name()
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data

        long_name = form_data['long_name']
        services.set_long_name(long_name)

        short_name = form_data['short_name']
        services.set_short_name(short_name)

        n_versions = form_data['versions']
        services.set_num_versions(n_versions)

        n_to_produce = form_data['num_to_produce']
        services.set_num_to_produce(n_to_produce)

        services.progress_set_names(True)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('upload')