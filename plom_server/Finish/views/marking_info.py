# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Aden Chan
# Copyright (C) 2025 Bryan Tanady


import json

import arrow

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Mark.services import MarkingTaskService
from plom_server.Papers.services import SpecificationService
from ..services import StudentMarkService, TaMarkingService, AnnotationDataService
from ..services import DataExtractionService, D3Service
from ..forms import StudentMarksFilterForm


class MarkingInformationView(ManagerRequiredView):
    """View for the Student Marks page."""

    template = "Finish/marking_landing.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the Student Marks HTML page."""
        mts = MarkingTaskService()
        d3s = D3Service()
        des = DataExtractionService()
        tms = TaMarkingService()

        context = self.build_context()

        papers = StudentMarkService().get_all_marks()
        n_questions = SpecificationService.get_n_questions()
        marked_question_counts = [
            [
                mts.get_marking_progress(version=v, question=q_idx)
                for v in SpecificationService.get_list_of_versions()
            ]
            for q_idx in SpecificationService.get_question_indices()
        ]
        (
            total_times_spent,
            average_times_spent,
            std_times_spent,
        ) = tms.all_marking_times_for_web(n_questions)

        hours_estimate = [
            tms.get_estimate_hours_remaining(qi)
            for qi in SpecificationService.get_question_indices()
        ]

        task_count_dict = mts.get_task_counts_dict()
        total_tasks = task_count_dict["all"]  # TODO: OUT_OF_DATE tasks? #2924
        all_marked = StudentMarkService.are_all_papers_marked() and total_tasks > 0

        # histogram of grades per question
        question_avgs = des.get_average_grade_on_all_questions()
        grades_hist_data = json.dumps(
            d3s.convert_stats_to_d3_hist_format(
                question_avgs, ylabel="Grade", title="Average Grade vs Question"
            )
        )

        # heatmap of correlation between questions
        corr_df = des._get_question_correlation_heatmap_data()
        # TODO: easily might've mixed up row/column here
        corr_heatmap_data = json.dumps(
            d3s.convert_correlation_to_d3_heatmap_format(
                corr_df.values,
                title="Question correlation",
                xlabels=corr_df.columns.to_list(),
                ylabels=corr_df.index.to_list(),
            )
        )

        context.update(
            {
                "papers": papers,
                "question_indices": SpecificationService.get_question_indices(),
                "version_list": SpecificationService.get_list_of_versions(),
                "marked_question_counts": marked_question_counts,
                "total_times_spent": total_times_spent,
                "average_times_spent": average_times_spent,
                "std_times_spent": std_times_spent,
                "all_marked": all_marked,
                "student_marks_form": StudentMarksFilterForm(),
                "hours_estimate": hours_estimate,
                "grades_hist_data": grades_hist_data,
                "corr_heatmap_data": corr_heatmap_data,
            }
        )

        return render(request, self.template, context)

    @staticmethod
    def marks_download(request: HttpRequest) -> HttpResponse:
        """Download marks as a csv file."""
        version_info = request.POST.get("version_info", "off") == "on"
        timing_info = request.POST.get("timing_info", "off") == "on"
        warning_info = request.POST.get("warning_info", "off") == "on"
        privacy_mode = request.POST.get("privacy_mode", "off") == "on"
        privacy_salt = request.POST.get("privacy_mode_salt", "")
        csv_as_string = StudentMarkService.build_marks_csv_as_string(
            version_info,
            timing_info,
            warning_info,
            privacy_mode=privacy_mode,
            privacy_salt=privacy_salt,
        )

        filename = (
            "marks--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response

    @staticmethod
    def ta_info_download(request: HttpRequest) -> HttpResponse:
        """Download TA marking information as a csv file."""
        tms = TaMarkingService()
        csv_as_string = tms.build_ta_info_csv_as_string()

        filename = (
            "TA--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response

    @staticmethod
    def annotation_info_download(request: HttpRequest) -> HttpResponse:
        """Download annotation information as a csv file."""
        ads = AnnotationDataService()
        csv_as_string = ads.get_csv_data_as_string()

        filename = (
            "annotations--"
            + SpecificationService.get_short_name_slug()
            + "--"
            + arrow.utcnow().format("YYYY-MM-DD--HH-mm-ss")
            + "--UTC"
            + ".csv"
        )

        response = HttpResponse(csv_as_string, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response


class MarkingInformationPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    def get(self, request: HttpRequest, *, paper_num: int) -> JsonResponse:
        """Get the data for the Student Marks page as a JSON blob."""
        marks_dict = StudentMarkService().get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)
