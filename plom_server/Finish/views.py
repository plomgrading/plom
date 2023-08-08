# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel

import csv
import json
from io import StringIO

import arrow

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Finish.services import DataExtractionService
from Mark.services import MarkingTaskService
from Papers.models import Specification
from SpecCreator.services import StagingSpecificationService
from .services import StudentMarkService, TaMarkingService, ReassembleService
from .forms import StudentMarksFilterForm


class MarkingInformationView(ManagerRequiredView):
    """View for the Student Marks page."""

    ras = ReassembleService()
    mts = MarkingTaskService()
    sms = StudentMarkService()
    smff = StudentMarksFilterForm()
    scs = StagingSpecificationService()
    tms = TaMarkingService()
    des = DataExtractionService()

    template = "Finish/marking_landing.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = self.scs.get_n_questions()
        n_versions = self.scs.get_n_versions()
        marked_question_counts = [
            [
                self.mts.get_marking_progress(version=v, question=q)
                for v in range(1, n_versions + 1)
            ]
            for q in range(1, n_questions + 1)
        ]
        (
            total_times_spent,
            average_times_spent,
            std_times_spent,
        ) = self.tms.all_marking_times_for_web(n_questions)

        days_estimate = [
            self.tms.get_estimate_days_remaining(q) for q in range(1, n_questions + 1)
        ]
        hours_estimate = [
            self.tms.get_estimate_hours_remaining(q) for q in range(1, n_questions + 1)
        ]

        total_tasks = self.mts.get_n_total_tasks()  # TODO: OUT_OF_DATE tasks? #2924
        all_marked = self.ras.are_all_papers_marked() and total_tasks > 0

        # histogram of grades per question
        question_avgs = self.des.get_average_grade_on_all_questions()
        grades_hist_data = self.sms.convert_stats_to_d3_hist_format(
            question_avgs, "Question number", "Grade", "Quesion vs Grade"
        )
        grades_hist_data = json.dumps(grades_hist_data)

        # heatmap of correlation between questions
        corr = self.des._get_question_correlation_heatmap_data().values
        corr_heatmap_data = self.sms.convert_correlation_to_d3_heatmap_format(
            corr, "Question correlation", "Question", "Question"
        )
        corr_heatmap_data = json.dumps(corr_heatmap_data)

        context.update(
            {
                "papers": papers,
                "n_questions": range(1, n_questions + 1),
                "n_versions": range(1, n_versions + 1),
                "marked_question_counts": marked_question_counts,
                "total_times_spent": total_times_spent,
                "average_times_spent": average_times_spent,
                "std_times_spent": std_times_spent,
                "all_marked": all_marked,
                "student_marks_form": self.smff,
                "hours_estimate": hours_estimate,
                "days_estimate": days_estimate,
                "grades_hist_data": grades_hist_data,
                "corr_heatmap_data": corr_heatmap_data,
            }
        )

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
