from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TestCreator.views import TestSpecPageView

from ..services import TestSpecService
from .. import forms


class TestSpecValidateView(TestSpecPageView):
    """Validate the test specification"""

    def build_context(self):
        context = super().build_context("validate")
        spec = TestSpecService()
        pages = spec.get_page_list()
        n_questions = spec.get_n_questions()
        n_pages = spec.get_n_pages()

        context.update({
            "num_pages": n_pages,
            "num_versions": spec.get_n_versions(),
            "id_page": spec.get_id_page_number(),
            "dnm_pages": ", ".join(f"p. {i}" for i in spec.get_dnm_page_numbers()),
            "total_marks": spec.get_total_marks()
        })

        questions = []
        for i in range(n_questions):
            question = {}
            question.update({
                "pages": ', '.join(f"p. {j}" for j in spec.get_question_pages(i+1)),
            })
            if i+1 in spec.questions:
                q_obj = spec.questions[i+1].get_question()
                if q_obj:
                    question.update({
                        "label": q_obj.label,
                        "mark": q_obj.mark,
                        "shuffle": spec.questions[i+1].get_question_fix_or_shuffle(),
                    })
                else:
                    question.update({
                        "label": "",
                        "mark": "",
                        "shuffle": "",
                    })
            questions.append(question)
        context.update({"questions": questions})
        return context

    def get(self, request):
        context = self.build_context()
        context.update({
            "form": forms.TestSpecValidateForm()
        })
        return render(request, "TestCreator/test-spec-validate-page.html", context)

    def post(self, request):
        form = forms.TestSpecValidateForm(request.POST)
        if form.is_valid():
            spec = TestSpecService()
            return HttpResponseRedirect(reverse('spec_submit'))
        else:
            context = self.build_context()
            context.update({
                "form": form,
            })
            return render(request, "TestCreator/test-spec-validate-page.html", context)
