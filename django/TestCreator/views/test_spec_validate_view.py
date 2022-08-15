from django.urls import reverse
from . import BaseTestSpecFormView
from ..services import TestSpecService
from .. import forms

class TestSpecValidateView(BaseTestSpecFormView):
    template_name = 'TestCreator/test-spec-validate-page.html'
    form_class = forms.TestSpecValidateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('validate', **kwargs)
        spec = TestSpecService()
        pages = spec.get_page_list()
        num_questions = spec.get_n_questions()

        context['num_pages'] = len(pages)
        context['num_versions'] = spec.get_n_versions()
        context['num_questions'] = num_questions
        context['id_page'] = spec.get_id_page_number()
        context['dnm_pages'] = ', '.join(f'p. {i}' for i in spec.get_dnm_page_numbers())
        context['total_marks'] = spec.get_total_marks()

        context['questions'] = []
        for i in range(num_questions):
            question = {}

            question['pages'] = ', '.join(f'p. {j}' for j in spec.get_question_pages(i+1))
            if i+1 in spec.questions:
                q_obj = spec.questions[i+1].get_question()
                question['label'] = q_obj.label
                question['mark'] = q_obj.mark
                question['shuffle'] = spec.questions[i+1].get_question_fix_or_shuffle()
            else:
                question['label'] = ''
                question['mark'] = ''
                question['shuffle'] = ''
            context['questions'].append(question)
        return context

    def form_valid(self, form):
        return super().form_valid(form, on_validate_page=True)

    def get_success_url(self):
        return reverse('spec_submit')