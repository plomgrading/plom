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
from django.contrib import messages

from ..services import (
    StudentMarkService,
    BuildStudentReportService,
    DataExtractionService,
)
from Base.base_group_views import ManagerRequiredView


class BuildStudentReportView(ManagerRequiredView):
    template = "Finish/build_student_report.html"

    def get(self, request):
        student_report_form = StudentIDForm()
        context = self.build_context()
        bsrs = BuildStudentReportService()
        (
            num_scanned,
            num_fully_marked,
            num_identified,
            num_ready,
        ) = bsrs.get_status_for_student_report()

        context.update(
            {
                "num_scanned": num_scanned,
                "num_fully_marked": num_fully_marked,
                "num_identified": num_identified,
                "num_ready": num_ready,
                "student_report_form": student_report_form,
            }
        )

        return render(request, self.template, context=context)

    def post(self, request):
        student_report_form = StudentIDForm(request.POST)
        context = self.build_context()
        bsrs = BuildStudentReportService()
        (
            num_scanned,
            num_fully_marked,
            num_identified,
            num_ready,
        ) = bsrs.get_status_for_student_report()

        context.update(
            {
                "num_scanned": num_scanned,
                "num_fully_marked": num_fully_marked,
                "num_identified": num_identified,
                "num_ready": num_ready,
                "student_report_form": student_report_form,
            }
        )

        if student_report_form.is_valid():
            choice = student_report_form.cleaned_data["choice"]
            input = student_report_form.cleaned_data["input"]

            if choice == "student_id":
                des = DataExtractionService()
                student_df = des.get_student_data()
                student_df_filtered = student_df[student_df["student_id"] == input]
                if student_df_filtered.empty:
                    messages.info(
                        request,
                        "Student ID is not recognized, maybe the paper has not been scanned?",
                    )
                    return render(request, self.template, context=context)
                else:
                    paper_number = student_df_filtered["paper_number"]
            else:
                paper_number = input

            try:
                paper = Paper.objects.get(paper_number=paper_number)
            except Paper.DoesNotExist:
                messages.info(request, "Paper is not recognized.")
                return render(request, self.template, context=context)

            sms = StudentMarkService()
            scanned, identified, num_marked, last_updated = sms.get_paper_status(paper)

            if not scanned:
                messages.info(request, "The paper has not been scanned yet.")
                return render(request, self.template, context=context)

            if not identified:
                messages.info(request, "The paper has not been identified yet.")
                return render(request, self.template, context=context)

            number_of_questions = SpecificationService.get_n_questions()
            if num_marked != number_of_questions:
                messages.info(request, "The paper has not been fully marked yet.")
                return render(request, self.template, context=context)

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
