import re
from django.urls import reverse
from . import BaseTestSpecFormPDFView
from ..services import TestSpecService
from .. import forms

class TestSpecCreatorQuestionDetailPage(BaseTestSpecFormPDFView):
    template_name = 'TestCreator/test-spec-question-detail-page.html'
    form_class = forms.TestSpecQuestionForm

    def get_initial(self):
        initial = super().get_initial()
        question_id = self.kwargs['q_idx']
        spec = TestSpecService()
        if spec.has_question(question_id):
            q_service = spec.questions[question_id]
            question = q_service.get_question()
            initial['label'] = question.label
            initial['mark'] = question.mark
            initial['shuffle'] = 'S' if question.shuffle else 'F'
        else:
            initial['label'] = f"Q{question_id}"

            # don't pre-fill the marks field
            # total_marks = services.get_total_marks()
            # initial['mark'] = total_marks // services.get_num_questions()

            if spec.get_n_versions() > 1:
                initial['shuffle'] = 'S'
            else:
                initial['shuffle'] = 'F'
        return initial

    def get_form_kwargs(self):
        """Pass the question index down to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['q_idx'] = self.kwargs['q_idx']
        return kwargs

    def get_context_data(self, **kwargs):
        question_id = self.kwargs['q_idx']
        context = super().get_context_data(f'question_{question_id}', **kwargs)
        spec = TestSpecService()

        context['question_id'] = question_id
        context['prev_id'] = question_id-1
        context['total_marks'] = spec.get_total_marks()
        if question_id in spec.questions:
            context['assigned_to_others'] = spec.questions[question_id].get_marks_assigned_to_other_questions()
        else:
            context['assigned_to_others'] = 0
        context['n_versions'] = spec.get_n_versions()

        context['x_data'] = spec.get_question_detail_page_alpine_xdata(question_id)
        context['pages'] = spec.get_pages_for_question_detail_page(question_id)

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        question_id = self.kwargs['q_idx']

        # save the question to the database
        label = form_data['label']
        mark = form_data['mark']
        shuffle = form_data['shuffle'] == 'S'
        
        spec = TestSpecService()
        spec.add_question(question_id, label, mark, shuffle)

        # save the question pages
        question_ids = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                question_ids.append(idx)
        spec.set_question_pages(question_ids, question_id)
        
        return super().form_valid(form)

    def get_success_url(self):
        question_id = self.kwargs['q_idx']
        print(question_id)
        spec = TestSpecService()
        num_questions = spec.get_n_questions()
        if question_id == num_questions:
            return reverse('dnm_page')
        else:
            return reverse('q_detail', args=(question_id+1,))