from django.urls import reverse
from . import BaseTestSpecFormView
from .. import services
from .. import forms

class TestSpecValidateView(BaseTestSpecFormView):
    template_name = 'TestCreator/test-spec-validate-page.html'
    form_class = forms.TestSpecValidateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('validate', **kwargs)
        pages = services.get_page_list()
        num_questions = services.get_num_questions()

        context['num_pages'] = len(pages)
        context['num_versions'] = services.get_num_versions()
        context['num_questions'] = num_questions
        context['id_page'] = services.get_id_page_number()
        context['dnm_pages'] = ', '.join(f'p. {i}' for i in services.get_dnm_page_numbers())
        context['total_marks'] = services.get_total_marks()

        context['questions'] = []
        for i in range(num_questions):
            question = {}

            # TODO: question get is 1-indexed??
            question['pages'] = ', '.join(f'p. {i}' for i in services.get_question_pages(i+1))
            question['label'] = services.get_question_label(i+1)
            question['mark'] = services.get_question_marks(i+1)
            question['shuffle'] = services.get_question_fix_or_shuffle(i+1)
            context['questions'].append(question)
        return context

    def form_valid(self, form):
        services.progress_set_validate_page(True)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('submit')