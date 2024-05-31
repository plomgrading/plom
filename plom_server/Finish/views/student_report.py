# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from django.shortcuts import render, redirect
import io
import zipfile
from django.http import HttpResponse

from .forms import StudentIDForm
from ..models import Paper
from Papers.services import SpecificationService
from Progress.services import ManageScanService

from ..services import (
    StudentMarkService,
    BuildStudentReportService,
    DataExtractionService,
)
from Base.base_group_views import ManagerRequiredView


class BuildStudentReportView(ManagerRequiredView):
    def get(self, request):
        student_report_form = StudentIDForm()
        return render(
            request,
            "Finish/build_student_report.html",
            {"student_report_form": student_report_form},
        )

    def post(self, request):
        student_report_form = StudentIDForm(request.POST)
        template = "Finish/build_student_report.html"
        if student_report_form.is_valid():
            choice = student_report_form.cleaned_data["choice"]
            input = student_report_form.cleaned_data["input"]

            if choice == "student_id":
                des = DataExtractionService()
                student_df = des.get_student_data()
                student_df_filtered = student_df[student_df["student_id"] == input]
                if student_df_filtered.empty:
                    return render(
                        request,
                        template,
                        {
                            "student_report_form": student_report_form,
                            "error_message": "Student ID is not recognized, maybe the paper has not been scanned?",
                        },
                    )
                else:
                    paper_number = student_df_filtered["paper_number"]
            else:
                paper_number = input

            try:
                paper = Paper.objects.get(paper_number=paper_number)
            except Paper.DoesNotExist:
                return render(
                    request,
                    template,
                    {
                        "student_report_form": student_report_form,
                        "error_message": "Paper is not recognized",
                    },
                )

            sms = StudentMarkService()
            scanned, identified, num_marked, last_updated = sms.get_paper_status(paper)

            if not scanned:
                return render(
                    request,
                    template,
                    {
                        "student_report_form": student_report_form,
                        "error_message": "The paper has not been scanned yet.",
                    },
                )
            if not identified:
                return render(
                    request,
                    template,
                    {
                        "student_report_form": student_report_form,
                        "error_message": "The paper has not been identified yet.",
                    },
                )

            number_of_questions = SpecificationService.get_n_questions()
            if num_marked != number_of_questions:
                return render(
                    request,
                    template,
                    {
                        "student_report_form": student_report_form,
                        "error_message": "The paper has not been fully marked yet.",
                    },
                )

            d = BuildStudentReportService.build_one_report(paper_number)
            response = HttpResponse(d["bytes"], content_type="application/pdf")
            response["Content-Disposition"] = f"attachment; filename={d['filename']}"
            return response

        return redirect("build_student_report")

    @staticmethod
    def build_all(request):
        papers = Paper.objects.all()
        memory_file = io.BytesIO()
        mss = ManageScanService()

        papers = mss.get_all_completed_test_papers()

        with zipfile.ZipFile(memory_file, "w") as zf:
            for paper_number in papers.keys():
                paper_info = StudentMarkService.get_paper_id_or_none(paper_number)
                if paper_info:
                    d = BuildStudentReportService.build_one_report(paper_number)
                    zf.writestr(d["filename"], d["bytes"])

        memory_file.seek(0)
        response = HttpResponse(memory_file, content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="all_reports.zip"'
        return response
