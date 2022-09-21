from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TestCreator.views import TestSpecPageView

from ..services import TestSpecService
from .. import forms


class TestSpecCreatorQuestionsPage(TestSpecPageView):
    """Set the number of questions and total marks"""

    def build_form(self):
        spec = TestSpecService()
        n_questions = spec.get_n_questions()
        marks = spec.get_total_marks()
        initial = {
            "questions": n_questions if n_questions > 0 else None,
            "total_marks": marks if marks > 0 else None,
        }

        form = forms.TestSpecQuestionsMarksForm(initial=initial)
        return form

    def build_context(self):
        context = super().build_context("questions")
        spec = TestSpecService()
        context.update(
            {
                "prev_n_questions": spec.get_n_questions(),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(
            request, "TestCreator/test-spec-questions-marks-page.html", context
        )

    def post(self, request):
        form = forms.TestSpecQuestionsMarksForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            spec = TestSpecService()

            prev_questions = spec.get_n_questions()
            n_questions = data["questions"]

            if prev_questions != n_questions:
                spec.clear_questions()
                spec.set_n_questions(n_questions)

            marks = data["total_marks"]
            print(marks)
            spec.set_total_marks(marks)

            spec.unvalidate()

            return HttpResponseRedirect(reverse("q_detail", args=(1,)))
        else:
            context = self.build_context()
            context.update({"form": form})
            return render(
                request, "TestCreator/test-spec-questions-marks-page.html", context
            )
