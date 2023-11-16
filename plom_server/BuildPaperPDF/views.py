# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import pathlib

from django.shortcuts import render
from django.template.loader import render_to_string

from django.http import FileResponse, StreamingHttpResponse
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService, PaperInfoService
from Preparation.services import PQVMappingService, StagingStudentService
from SpecCreator.services import StagingSpecificationService

from .models import PDFTask
from .services import BuildPapersService, RenamePDFFile


class BuildPaperPDFs(ManagerRequiredView):
    template_name = "BuildPaperPDF/build_paper_pdfs.html"

    def table_fragment(self, request):
        """Get the current state of the tasks, render it as an HTML table, and return."""
        bps = BuildPapersService()
        task_context = bps.get_task_context()

        running_tasks = bps.get_n_running_tasks()
        if running_tasks > 0:
            poll = True
        else:
            poll = False

        if bps.get_n_complete_tasks() == bps.get_n_tasks():
            zip_disabled = False
        else:
            zip_disabled = True

        table_fragment = render_to_string(
            "BuildPaperPDF/fragments/pdf_table.html",
            {
                "tasks": task_context,
                "poll": poll,
                "zip_disabled": zip_disabled,
            },
            request=request,
        )

        return table_fragment

    def get(self, request):
        bps = BuildPapersService()
        pqvs = PQVMappingService()
        pinfo = PaperInfoService()
        qvmap = pqvs.get_pqv_map_dict()
        num_pdfs = len(qvmap)

        n_tasks = bps.get_n_tasks()
        if n_tasks > 0:
            pdfs_staged = True
        else:
            pdfs_staged = False

        table_fragment = self.table_fragment(request)

        zip_disabled = True
        n_completed_tasks = bps.get_n_complete_tasks()
        if n_completed_tasks == n_tasks:
            zip_disabled = False

        context = self.build_context()
        context.update(
            {
                "message": "",
                "zip_disabled": zip_disabled,
                "num_pdfs": num_pdfs,
                "pdfs_staged": pdfs_staged,
                "pdf_table": table_fragment,
                "db_initialised": pinfo.is_paper_database_populated(),
            }
        )

        return render(request, self.template_name, context)

    def post(self, request):
        bps = BuildPapersService()
        sstu = StagingStudentService()
        classdict = sstu.get_classdict()

        # bps.clear_tasks()
        bps.stage_all_pdf_jobs(classdict=classdict)
        task_context = bps.get_task_context()

        table_fragment = self.table_fragment(request)

        context = self.build_context()
        context.update(
            {
                "message": "",
                "tasks": task_context,
                "zip_disabled": True,
                "pdfs_staged": True,
                "pdf_table": table_fragment,
            }
        )

        return render(request, self.template_name, context)


class PDFTableView(ManagerRequiredView):
    def render_pdf_table(self, request):
        bps = BuildPapersService()
        task_context = bps.get_task_context()

        n_complete = bps.get_n_complete_tasks()
        n_total = len(task_context)
        if n_total > 0:
            percent_complete = n_complete / n_total * 100
        else:
            percent_complete = 0

        zip_disabled = True
        status = 200
        if n_complete == n_total:
            status = 286
            zip_disabled = False

        n_running = bps.get_n_running_tasks()
        poll = n_running > 0

        context = self.build_context()
        context.update(
            {
                "tasks": task_context,
                "pdf_errors": bps.are_there_errors(),
                "message": f"Progress: {n_complete} papers of {n_total} built ({percent_complete:.0f}%)",
                "zip_disabled": zip_disabled,
                "poll": poll,
            }
        )

        return render(
            request, "BuildPaperPDF/fragments/pdf_table.html", context, status=status
        )


class UpdatePDFTable(PDFTableView):
    """Get an updated pdf-building-progress table."""

    def get(self, request):
        return self.render_pdf_table(request)


class GetPDFFile(ManagerRequiredView):
    def get(self, request, paper_number):
        try:
            (pdf_filename, pdf_bytes) = BuildPapersService().get_paper_path_and_bytes(
                paper_number
            )
        except ValueError:
            return render(request, "BuildPaperPDF/cannot_find_pdf.html")

        pdf = SimpleUploadedFile(
            pdf_filename, pdf_bytes, content_type="application/pdf"
        )

        return FileResponse(pdf)


class GetStreamingZipOfPDFs(ManagerRequiredView):
    """Get the completed test paper PDFs in one zip file."""

    # using zipfly python package.  see django example here
    # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
    def get(self, request):
        short_name = StagingSpecificationService().get_short_name_slug()
        zgen = BuildPapersService().get_zipfly_generator(short_name)
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = f"attachment; filename={short_name}.zip"
        return response


class StartAllPDFs(PDFTableView):
    def post(self, request):
        bps = BuildPapersService()
        spec = SpecificationService.get_the_spec()
        pqvs = PQVMappingService()
        qvmap = pqvs.get_pqv_map_dict()

        bps.send_all_tasks(spec, qvmap)

        return self.render_pdf_table(request)


class StartOnePDF(PDFTableView):
    def post(self, request, paper_number):
        bps = BuildPapersService()
        spec = SpecificationService.get_the_spec()
        pqvs = PQVMappingService()
        qvmap = pqvs.get_pqv_map_dict()

        bps.send_single_task(paper_number, spec, qvmap[paper_number])
        return self.render_pdf_table(request)


class CancelAllPDf(PDFTableView):
    def post(self, request):
        bps = BuildPapersService()
        bps.cancel_all_task()

        return self.render_pdf_table(request)


class CancelOnePDF(PDFTableView):
    def post(self, request, paper_number):
        bps = BuildPapersService()
        bps.cancel_single_task(paper_number)

        return self.render_pdf_table(request)


class RetryAllPDF(PDFTableView):
    def post(self, request):
        bps = BuildPapersService()
        spec = SpecificationService.get_the_spec()
        pqvs = PQVMappingService()
        qvmap = pqvs.get_pqv_map_dict()

        bps.retry_all_task(spec, qvmap)

        return self.render_pdf_table(request)


class DeleteAllPDFs(ManagerRequiredView):
    def post(self, request):
        BuildPapersService().reset_all_tasks()

        return HttpResponseClientRedirect(reverse("create_paperPDFs"))
