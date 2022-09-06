import re
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TestCreator.views import TestSpecPDFView

from ..services import TestSpecService
from .. import forms


class TestSpecCreatorQuestionDetailPage(TestSpecPDFView):
    """Select pages, max mark, and shuffle status for a question."""

    def build_form(self, question_id):
        spec = TestSpecService()
        initial = {}
        if spec.has_question(question_id):
            q_service = spec.questions[question_id]
            question = q_service.get_question()
            initial.update({
                "label": question.label,
                "mark": question.mark,
                "shuffle": 'S' if question.shuffle else 'F',
            })
        else:
            initial.update({'label': f"Q{question_id}"})
            if spec.get_n_versions() > 1:
                initial.update({'shuffle': 'S'})
            else:
                initial.update({'shuffle': 'F'})

        n_pages = spec.get_n_pages()
        form = forms.TestSpecQuestionForm(n_pages, initial=initial, q_idx=question_id)
        return form

    def build_context(self, question_id):
        context = super().build_context(f"question_{question_id}")
        spec = TestSpecService()

        context.update({
            "question_id": question_id,
            "prev_id": question_id - 1,
            "total_marks": spec.get_total_marks(),
            "n_versions": spec.get_n_versions(),
            "n_questions": spec.get_n_questions(),
            "x_data": spec.get_question_detail_page_alpine_xdata(question_id),
            "pages": spec.get_pages_for_question_detail_page(question_id),
        })

        if question_id in spec.questions:
            context.update({
                "assigned_to_others": spec.questions[question_id].get_marks_assigned_to_other_questions()
            })
        else:
            context.update({"assigned_to_others": 0})

        return context

    def get(self, request, q_idx):
        context = self.build_context(q_idx)
        context.update({
            'form': self.build_form(q_idx),
        })
        return render(request, "TestCreator/test-spec-question-detail-page.html", context)

    def post(self, request, q_idx):
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        form = forms.TestSpecQuestionForm(n_pages, request.POST, q_idx=q_idx)

        if form.is_valid():
            data = form.cleaned_data
            label = data['label']
            mark = data['mark']
            shuffle = (data['shuffle'] == 'S')
            spec.add_question(q_idx, label, mark, shuffle)

            question_ids = []
            for key, value in data.items():
                if 'page' in key and value == True:
                    idx = int(re.sub('\D', '', key))
                    question_ids.append(idx)
            spec.set_question_pages(question_ids, q_idx)

            spec.unvalidate()

            return HttpResponseRedirect(self.get_success_url(q_idx))
        else:
            context = self.build_context(q_idx)
            context.update({"form": form})
            return render(request, "TestCreator/test-spec-question-detail-page.html", context)

    def get_success_url(self, q_idx):
        spec = TestSpecService()
        n_questions = spec.get_n_questions()
        if q_idx == n_questions:
            return reverse('dnm_page')
        else:
            return reverse('q_detail', args=(q_idx+1,))
