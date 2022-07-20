import re
from django.urls import reverse
from . import BaseTestSpecFormPDFView
from .. import forms
from .. import services

class TestSpecCreatorQuestionDetailPage(BaseTestSpecFormPDFView):
    template_name = 'test_creator/test-spec-question-detail-page.html'
    form_class = forms.TestSpecQuestionForm

    def get_initial(self):
        # TODO: pre-populate marks field
        initial = super().get_initial()
        question_id = self.kwargs['q_idx']
        if services.question_exists(question_id):
            question = services.get_question(question_id)
            initial['label'] = question.label
            initial['mark'] = question.mark
            initial['shuffle'] = question.shuffle
        else:
            initial['label'] = f"Q{question_id}"

            total_marks = services.get_total_marks()
            initial['mark'] = total_marks // services.get_num_questions()

            if services.get_num_versions() > 1:
                initial['shuffle'] = 'S'
            else:
                initial['shuffle'] = 'F'
        return initial

    def get_context_data(self, **kwargs):
        question_id = self.kwargs['q_idx']
        context = super().get_context_data(f'question_{question_id}', **kwargs)
        context['question_id'] = question_id
        context['prev_id'] = question_id-1
        context['total_marks'] = services.get_total_marks()
        context['n_versions'] = services.get_num_versions()

        context['x_data'] = services.get_question_detail_page_alpine_xdata(question_id)
        context['pages'] = services.get_pages_for_question_detail_page(question_id)

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        question_id = self.kwargs['q_idx']

        # save the question to the database
        label = form_data['label']
        mark = form_data['mark']
        shuffle = form_data['shuffle']

        services.create_or_replace_question(question_id, label, mark, shuffle)

        # save the question pages
        question_ids = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                question_ids.append(idx)
        services.set_question_pages(question_ids, question_id)

        services.progress_set_question_detail_page(question_id-1, True)
        
        return super().form_valid(form)

    def get_success_url(self):
        question_id = self.kwargs['q_idx']
        num_questions = services.get_num_questions()
        if question_id == num_questions:
            return reverse('dnm_page')
        else:
            return reverse('q_detail', args=(question_id + 1,))