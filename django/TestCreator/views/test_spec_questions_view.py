from django.urls import reverse
from . import BaseTestSpecFormView
from .. import forms
from .. import services

class TestSpecCreatorQuestionsPage(BaseTestSpecFormView):
    template_name = 'TestCreator/test-spec-questions-marks-page.html'
    form_class = forms.TestSpecQuestionsMarksForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('questions', **kwargs)
        context['prev_n_questions'] = services.get_num_questions()
        return context

    def get_initial(self):
        initial = super().get_initial()
        if services.get_num_questions() > 0:
            initial['questions'] = services.get_num_questions()
        if services.get_total_marks() > 0:
            initial['total_marks'] = services.get_total_marks()

        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data

        prev_questions = services.get_num_questions()
        services.set_total_marks(form_data['total_marks'])

        services.progress_set_question_page(True)
        if prev_questions != form_data['questions']:
            services.clear_questions()
            services.set_num_questions(form_data['questions'])
            services.progress_init_questions()
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('q_detail', args=(1,))