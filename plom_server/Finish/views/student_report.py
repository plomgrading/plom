# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald

import io
import zipfile
from urllib.parse import quote

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from Papers.models import Paper
from Progress.services import ManageScanService
from ..services import (
    StudentMarkService,
    BuildStudentReportService,
    DataExtractionService,
)
from .forms import StudentIDForm


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

            if choice == "studentID":
                des = DataExtractionService()
                student_df = des.get_student_data()
                student_df_filtered = student_df[student_df["studentID"] == input]
                if student_df_filtered.empty:
                    messages.info(
                        request,
                        "Student ID is not recognized, maybe the paper has not been scanned?",
                    )
                    return render(request, self.template, context=context)
                else:
                    paper_number = student_df_filtered["paper_number"].iloc[0]
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
            bsrs = BuildStudentReportService()
            d = bsrs.build_one_report(paper_number=paper_number)
            response = HttpResponse(d["bytes"], content_type="application/pdf")
            encoded_filename = quote(d["filename"])
            response["Content-Disposition"] = f"attachment; filename={encoded_filename}"
            return response

        return redirect("build_student_report")

    @staticmethod
    def build_all(request):
        papers = Paper.objects.all()
        memory_file = io.BytesIO()
        mss = ManageScanService()

        papers = mss.get_all_completed_test_papers()

        with zipfile.ZipFile(memory_file, "w") as zf:
            sms = StudentMarkService()
            number_of_questions = SpecificationService.get_n_questions()
            for paper_number in papers.keys():
                paper = Paper.objects.get(paper_number=paper_number)
                scanned, identified, num_marked, last_updated = sms.get_paper_status(
                    paper
                )
                if scanned and identified and num_marked == number_of_questions:
                    bsrs = BuildStudentReportService()
                    d = bsrs.build_one_report(paper_number=paper_number)
                    zf.writestr(d["filename"], d["bytes"])

        memory_file.seek(0)
        response = HttpResponse(memory_file, content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="all_reports.zip"'
        return response
