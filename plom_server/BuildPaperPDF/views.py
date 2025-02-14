# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy

from __future__ import annotations

from typing import Any
from io import BytesIO

from django.shortcuts import render
from django.template.loader import render_to_string

from django.http import HttpRequest, HttpResponse
from django.http import FileResponse, StreamingHttpResponse, Http404
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse

from django.contrib import messages

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService, PaperInfoService
from .services import BuildPapersService

from plom.plom_exceptions import PlomDependencyConflict


def _task_context_and_status() -> tuple[dict[str, Any], int]:
    db_initialised = PaperInfoService.is_paper_database_populated()
    bps = BuildPapersService()
    n_complete = bps.get_n_complete_tasks()
    n_papers = bps.get_n_papers()
    # Note: task_context could be longer if we include obsoletes
    task_context = bps.get_task_context()
    # task_context = bps.get_task_context(include_obsolete=True)

    if not db_initialised:
        msg = "Nothing to build; have you initialised the database?"
    elif n_papers == 0:
        msg = f"There are {n_papers} papers to be built (none triggered)."
    else:
        _percent = n_complete / n_papers * 100
        msg = f"Progress: {n_complete} papers of {n_papers} built ({_percent:.0f}%)"

    zip_enabled = False
    if db_initialised and n_complete == n_papers:
        zip_enabled = True

    status = 200
    if n_complete == n_papers:
        status = 286

    n_running = bps.get_n_tasks_started_but_not_complete()
    poll = n_running > 0

    d = {
        "tasks": task_context,
        "pdf_errors": bps.are_there_errors(),
        "message": msg,
        "zip_enabled": zip_enabled,
        "poll": poll,
        "db_initialised": db_initialised,
        "papers_built": n_complete > 0,
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
        # Here we build an initial version of the table, which is likely to be updated
        # later via various HTMX or other refresh calls.
        table_fragment = self._table_fragment(request)
        context = self.build_context()
        context.update(
            {
                "pdf_table": table_fragment,
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
            (pdf_filename, pdf_bytes) = (
                BuildPapersService().get_paper_recommended_name_and_bytes(paper_number)
            )
        except ValueError:
            # TODO: Issue #3157 why do we need this?  Can we just 404?
            return render(request, "BuildPaperPDF/cannot_find_pdf.html")

        return FileResponse(
            BytesIO(pdf_bytes), filename=pdf_filename, content_type="application/pdf"
        )


class GetStreamingZipOfPDFs(ManagerRequiredView):
    """Get the generated papers as PDFs in one zip file."""

    # using zipfly python package.  see django example here
    # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
    def get(self, request: HttpRequest) -> HttpResponse:
        short_name = SpecificationService.get_short_name_slug()
        try:
            zgen = BuildPapersService().get_zipfly_generator(short_name)
        except ValueError as e:
            raise Http404(e)
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = f"attachment; filename={short_name}.zip"
        return response


class StartAllPDFs(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        try:
            bps.send_all_tasks()
            return self.render_pdf_table(request)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))


class StartOnePDF(PDFTableView):
    def post(self, request: HttpRequest, paper_number: int) -> HttpResponse:
        bps = BuildPapersService()
        try:
            bps.send_single_task(paper_number)
            return self.render_pdf_table(request)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))


class CancelAllPDFs(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        bps.try_to_cancel_all_queued_tasks()
        return self.render_pdf_table(request)


class RetryAllPDF(PDFTableView):
    def post(self, request: HttpRequest) -> HttpResponse:
        bps = BuildPapersService()
        try:
            bps.retry_all_task()
            return self.render_pdf_table(request)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))


class DeleteAllPDFs(ManagerRequiredView):

    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            BuildPapersService().reset_all_tasks()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

        return HttpResponseClientRedirect(reverse("create_paperPDFs"))
