# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import json

from django.shortcuts import render
from django.http import JsonResponse

from Base.base_group_views import ManagerRequiredView
from StudentMarks.services import StudentMarksService
from SpecCreator.services import StagingSpecificationService


class StudentMarkView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarksService()
    scs = StagingSpecificationService()
    template = "StudentMarks/all_student_marks.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        marked_percentages = [self.sms.get_n_of_question_marked(q) for q in range(1, n_questions + 1)]

        context.update(
            {
                "papers": papers,
                "n_questions": range(1, n_questions + 1),
                "n_papers": len(papers),
                "marked_percentages": marked_percentages,
            }
        )

        # return JsonResponse(student_marks)
        return render(request, self.template, context)


class StudentMarkPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "StudentMarks/paper_marks.html"
    sms = StudentMarksService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
