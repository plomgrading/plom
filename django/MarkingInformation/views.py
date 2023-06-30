# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import csv
from io import StringIO

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User

from Base.base_group_views import ManagerRequiredView
from Papers.models import Specification
from SpecCreator.services import StagingSpecificationService
from MarkingInformation.services.student_marks_service import StudentMarkService
from MarkingInformation.services.ta_marking_service import TaMarkingService
from Papers.models import Paper


class MarkingInformationView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarkService()
    tms = TaMarkingService()
    scs = StagingSpecificationService()
    template = "MarkingInformation/marking_landing.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        marked_percentages = [
            self.sms.get_n_of_question_marked(q) for q in range(1, n_questions + 1)
        ]
        total_times_spent = [
            self.tms.get_time_spent_on_question(question=q)
            for q in range(1, n_questions + 1)
        ]
        average_times_spent = [
            self.tms.get_time_spent_on_question(question=q, average=True)
            for q in range(1, n_questions + 1)
        ]

        context.update(
            {
                "papers": papers,
                "n_questions": range(1, n_questions + 1),
                "n_papers": len(papers),
                "marked_percentages": marked_percentages,
                "total_times_spent": total_times_spent,
                "average_times_spent": average_times_spent,
            }
        )

        # return JsonResponse(student_marks)
        return render(request, self.template, context)

    def marks_download(request):
        """Download marks as a csv file."""
        sms = StudentMarkService()
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

    def ta_info_download(request):
        """Download TA marking information as a csv file."""
        tms = TaMarkingService()
        ta_info = tms.build_csv_data()

        keys = tms.get_csv_header()
        response = None
        f = StringIO()

        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(ta_info)

        f.seek(0)

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ta_marking_info.csv"'

        return response


class MarkingInformationPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "MarkingInformation/paper_marks.html"
    sms = StudentMarkService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
