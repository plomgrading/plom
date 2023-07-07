# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import arrow
import csv
from io import StringIO

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.models import Specification
from SpecCreator.services import StagingSpecificationService
from Finish.services import StudentMarkService, TaMarkingService
from Finish.forms import StudentMarksFilterForm


class MarkingInformationView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarkService()
    smff = StudentMarksFilterForm()
    tms = TaMarkingService()
    scs = StagingSpecificationService()

    template = "Finish/marking_landing.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        marked_question_counts = [
            self.sms.get_n_of_question_marked(q) for q in range(1, n_questions + 1)
        ]
        (
            total_times_spent,
            average_times_spent,
            std_times_spent,
        ) = self.tms.all_marking_times_for_web(n_questions)

        estimate_days = self.tms.get_estimate_days_remaining(3)
        estimate_hours = self.tms.get_estimate_hours_remaining(3)

        context.update(
            {
                "papers": papers,
                "n_questions": range(1, n_questions + 1),
                "n_papers": len(papers),
                "marked_question_counts": marked_question_counts,
                "total_times_spent": total_times_spent,
                "average_times_spent": average_times_spent,
                "std_times_spent": std_times_spent,
                "all_marked": True,
                "student_marks_form": self.smff,
                "estimate_days": estimate_days,
                "estimate_hours": estimate_hours,
            }
        )

        for marked_question_count in marked_question_counts:
            if marked_question_count < len(papers):
                context["all_marked"] = False
                break

        return render(request, self.template, context)

    def marks_download(request):
        """Download marks as a csv file."""
        sms = StudentMarkService()
        version_info = request.POST.get("version_info", "off") == "on"
        timing_info = request.POST.get("timing_info", "off") == "on"
        warning_info = request.POST.get("warning_info", "off") == "on"
        spec = Specification.load().spec_dict

        # create csv file headers
        keys = sms.get_csv_header(spec, version_info, timing_info, warning_info)
        student_marks = sms.get_all_students_download(
            version_info, timing_info, warning_info
        )

        f = StringIO()

        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(student_marks)

        f.seek(0)

        filename = (
            "marks--"
            + spec["name"]
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response

    def ta_info_download(request):
        """Download TA marking information as a csv file."""
        tms = TaMarkingService()
        ta_info = tms.build_csv_data()
        spec = Specification.load().spec_dict

        keys = tms.get_csv_header()
        response = None
        f = StringIO()

        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(ta_info)

        f.seek(0)

        filename = (
            "TA--"
            + spec["name"]
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response


class MarkingInformationPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    sms = StudentMarkService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
