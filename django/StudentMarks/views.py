# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse

from Base.base_group_views import ManagerRequiredView
from StudentMarks.services import StudentMarksService
from SpecCreator.services import StagingSpecificationService
from Papers.models import Specification


class StudentMarkView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarksService()
    scs = StagingSpecificationService()
    template = "StudentMarks/all_student_marks.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        marked_percentages = [self.sms.get_n_of_question_marked(
            q) for q in range(1, n_questions + 1)]

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

    def marks_download(request):
        """Download marks as a csv file."""
        import csv

        sms = StudentMarksService()
        spec = Specification.load().spec_dict
        student_marks = sms.get_all_marks_download()

        response = None

        # create csv file headers
        keys = ["paper"]
        for q in range(1, spec["numberOfQuestions"]+1):
            keys.append("Q" + str(q) + "_mark")
            keys.append("Q" + str(q) + "_version")

        with open('marks.csv', 'w') as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            w.writerows(student_marks)

        with open('marks.csv', 'r') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=marks.csv'

        return response


class StudentMarkPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "StudentMarks/paper_marks.html"
    sms = StudentMarksService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
