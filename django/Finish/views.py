# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import csv
from io import StringIO

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.models import Specification
from SpecCreator.services import StagingSpecificationService
from Finish.services import StudentMarksService


class StudentMarkView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarksService()
    scs = StagingSpecificationService()
    template = "Finish/all_student_marks.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        marked_percentages = [
            self.sms.get_n_of_question_marked(q) for q in range(1, n_questions + 1)
        ]

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
        sms = StudentMarksService()
        spec = Specification.load().spec_dict
        student_marks = sms.get_all_students_download()

        response = None

        # create csv file headers
        keys = sms.get_csv_header(spec)

        f = StringIO()

        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(student_marks)

        f.seek(0)

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="marks.csv"'

        return response


class StudentMarkPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "Finish/paper_marks.html"
    sms = StudentMarksService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
