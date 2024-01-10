# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer

import csv
import json
from io import StringIO

import arrow

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from ..services import StudentMarkService, TaMarkingService
from ..services import DataExtractionService, D3Service
from ..forms import StudentMarksFilterForm


class MarkingInformationView(ManagerRequiredView):
    """View for the Student Marks page."""

    def __init__(self):
        self.mts = MarkingTaskService()
        self.sms = StudentMarkService()
        self.smff = StudentMarksFilterForm()
        self.tms = TaMarkingService()
        self.des = DataExtractionService()
        self.d3s = D3Service()

    template = "Finish/marking_landing.html"

    def get(self, request):
        context = self.build_context()

        papers = self.sms.get_all_marks()
        n_questions = SpecificationService.get_n_questions()
        n_versions = SpecificationService.get_n_versions()
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

        hours_estimate = [
            self.tms.get_estimate_hours_remaining(q) for q in range(1, n_questions + 1)
        ]

        total_tasks = self.mts.get_n_total_tasks()  # TODO: OUT_OF_DATE tasks? #2924
        all_marked = self.sms.are_all_papers_marked() and total_tasks > 0

        # histogram of grades per question
        question_avgs = self.des.get_average_grade_on_all_questions()
        grades_hist_data = self.d3s.convert_stats_to_d3_hist_format(
            question_avgs, ylabel="Grade", title="Average Grade vs Question"
        )
        grades_hist_data = json.dumps(grades_hist_data)

        # heatmap of correlation between questions
        corr_df = self.des._get_question_correlation_heatmap_data()
        # TODO: easily might've mixed up row/column here
        corr_heatmap_data = self.d3s.convert_correlation_to_d3_heatmap_format(
            corr_df.values,
            title="Question correlation",
            xlabels=corr_df.columns.to_list(),
            ylabels=corr_df.index.to_list(),
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
                "grades_hist_data": grades_hist_data,
                "corr_heatmap_data": corr_heatmap_data,
            }
        )

        return render(request, self.template, context)

    @staticmethod
    def marks_download(request):
        """Download marks as a csv file."""
        sms = StudentMarkService()

        version_info = request.POST.get("version_info", "off") == "on"
        timing_info = request.POST.get("timing_info", "off") == "on"
        warning_info = request.POST.get("warning_info", "off") == "on"
        spec = SpecificationService.get_the_spec()

        # create csv file headers
        keys = sms.get_csv_header(spec, version_info, timing_info, warning_info)
        student_marks = sms.get_all_students_download(
            version_info, timing_info, warning_info
        )

        f = StringIO()

        # ignore any extra fields in the dictionary.
        w = csv.DictWriter(f, keys, extrasaction="ignore")
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

    @staticmethod
    def ta_info_download(request):
        """Download TA marking information as a csv file."""
        tms = TaMarkingService()
        ta_info = tms.build_csv_data()
        spec = SpecificationService.get_the_spec()

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
