# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from typing import Any

from django.shortcuts import render
from django.template.loader import render_to_string

from django.http import HttpRequest, HttpResponse
from django.http import FileResponse, StreamingHttpResponse
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService, PaperInfoService


from .services import BuildPapersService


def _task_context_and_status() -> tuple[dict[str, Any], int]:
    db_initialised = PaperInfoService().is_paper_database_populated()
    db_num_papers = PaperInfoService().how_many_papers_in_database()
    bps = BuildPapersService()
    task_context = bps.get_task_context()

    n_complete = bps.get_n_complete_tasks()
    n_total = len(task_context)
    if not db_initialised:
        msg = "Nothing to build; have you initialised the database?"
    elif n_total == 0:
        msg = f"There are {db_num_papers} papers to be built (none triggered)."
    else:
        percent = n_complete / n_total * 100
        msg = f"Progress: {n_complete} papers of {n_total} built ({percent:.0f}%)"

    zip_disabled = True
    if n_total > 0 and n_complete == n_total:
        zip_disabled = False

    status = 200
    if n_complete == n_total:
        status = 286

    n_running = bps.get_n_tasks_started_but_not_complete()
    poll = n_running > 0

    d = {
        "tasks": task_context,
        "pdf_errors": bps.are_there_errors(),
        "message": msg,
        "zip_disabled": zip_disabled,
        "poll": poll,
        "db_initialised": db_initialised,
    }
    return d, status


class BuildPaperPDFs(ManagerRequiredView):
    template_name = "BuildPaperPDF/build_paper_pdfs.html"

    def _table_fragment(self, request: HttpRequest) -> str:
        """Get the current state of the tasks, render it as an HTML table, and return."""
        context, _ = _task_context_and_status()
        table_fragment = render_to_string(
            "BuildPaperPDF/fragments/pdf_table.html",
            context,
            request=request,
        )
        return table_fragment

    def get(self, request: HttpRequest) -> HttpResponse:
        pinfo = PaperInfoService()
        table_fragment = self._table_fragment(request)
        context = self.build_context()
        context.update(
            {
                "pdf_table": table_fragment,
                "db_initialised": pinfo.is_paper_database_populated(),
            }
        )
        return render(request, self.template_name, context)


class PDFTableView(ManagerRequiredView):
    def render_pdf_table(self, request: HttpRequest) -> HttpResponse:
        d, status = _task_context_and_status()
        context = self.build_context()
        context.update(d)
        return render(
            request, "BuildPaperPDF/fragments/pdf_table.html", context, status=status
        )


class UpdatePDFTable(PDFTableView):
    """Get an updated pdf-building-progress table."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return self.render_pdf_table(request)


class GetPDFFile(ManagerRequiredView):
    def get(self, request: HttpRequest, paper_number: int) -> HttpResponse:
        try:
            (pdf_filename, pdf_bytes) = BuildPapersService().get_paper_path_and_bytes(
                paper_number
            )
        except ValueError:
            # TODO: Issue #3157 why do we need this?  Can we just 404?
            return render(request, "BuildPaperPDF/cannot_find_pdf.html")

        pdf = SimpleUploadedFile(
            pdf_filename, pdf_bytes, content_type="application/pdf"
        )

        return FileResponse(pdf)


class GetStreamingZipOfPDFs(ManagerRequiredView):
    """Get the completed test paper PDFs in one zip file."""

    # using zipfly python package.  see django example here
    # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
    def get(self, request: HttpRequest) -> HttpResponse:
        short_name = SpecificationService.get_short_name_slug()
        zgen = BuildPapersService().get_zipfly_generator(short_name)
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = f"attachment; filename={short_name}.zip"
        return response


class StartAllPDFs(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        bps.send_all_tasks()
        return self.render_pdf_table(request)


class StartOnePDF(PDFTableView):
    def post(self, request: HttpRequest, paper_number: int) -> HttpResponse:
        bps = BuildPapersService()
        bps.send_single_task(paper_number)
        return self.render_pdf_table(request)


class CancelAllPDFs(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        bps.try_to_cancel_all_queued_tasks()
        return self.render_pdf_table(request)


class CancelOnePDF(PDFTableView):
    def post(self, request: HttpRequest, paper_number: int) -> HttpResponse:
        bps = BuildPapersService()
        bps.try_to_cancel_single_queued_task(paper_number)
        return self.render_pdf_table(request)


class RetryAllPDF(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        bps.retry_all_task()
        return self.render_pdf_table(request)


class DeleteAllPDFs(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        BuildPapersService().reset_all_tasks()

        return HttpResponseClientRedirect(reverse("create_paperPDFs"))
