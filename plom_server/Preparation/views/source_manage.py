# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    HttpRequest,
    HttpResponse,
    FileResponse,
    Http404,
    HttpResponseBadRequest,
)
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib import messages

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService

from ..services import SourceService


class SourceManageView(ManagerRequiredView):
    def build_context(self):
        server_paper_size_name = Settings.get_paper_size()
        sources = SourceService.get_list_of_sources()
        paper_warnings = []
        sizes = []
        for src in sources:
            sz = src.get("paper_size_name")
            if sz:
                sizes.append(sz)
                if sz != server_paper_size_name:
                    paper_warnings.append(
                        f'version {src["version"]} paper size "{sz}" '
                        f'does not match server "{server_paper_size_name}"'
                    )
        if len(set(sizes)) > 1:
            paper_warnings.append(
                f"Inconsistent paper sizes between versions: {set(sizes)}"
            )

        return {
            "number_of_pages": SpecificationService.get_n_pages(),
            "sources": sources,
            "all_sources_uploaded": SourceService.are_all_sources_uploaded(),
            "duplicates": SourceService.check_pdf_duplication(),
            "server_paper_size_name": server_paper_size_name,
            "paper_warnings": paper_warnings,
        }

    def get(self, request: HttpRequest, *, version: int | None = None) -> HttpResponse:
        """Get to render the sources management page or specify a version to download a PDF."""
        # if no spec then redirect to the dependency conflict page
        if not SpecificationService.is_there_a_spec():
            messages.add_message(
                request,
                messages.ERROR,
                "You cannot upload source pdfs until there is an assessment specification.",
            )
            return redirect(reverse("prep_conflict"))

        if version is not None:
            try:
                original_filename, abstract_django_file = (
                    SourceService._get_source_file(version)
                )
                return FileResponse(
                    abstract_django_file,
                    as_attachment=True,
                    filename=original_filename,
                )
            except ObjectDoesNotExist as e:
                raise Http404(e)

        context = self.build_context()
        return render(request, "Preparation/source_manage.html", context)

    def post(self, request: HttpRequest, *, version: int | None = None) -> HttpResponse:
        """HTMX posts here will add a new source PDF file to the server.

        On success, this re-renders the particular card for this version.

        On errors, this returns 400 or 409 http response, with plain
        textual human-readable error messages.  The error messages
        are undecorated.
        """
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX POST requests are allowed")

        context = self.build_context()
        try:
            pdf = request.FILES["source_pdf"]
        except KeyError as err:
            return HttpResponseBadRequest(f"Missing file, no field {err}")

        if version is None:
            return HttpResponseBadRequest("Only supports uploading by version")

        try:
            SourceService.take_source_from_upload(version, pdf)
        except PlomDependencyConflict as err:
            return HttpResponse(err, status=409)
        except ValueError as err:
            return HttpResponse(err, status=400)
        context.update({"src": SourceService.get_source_info(version)})
        return render(request, "Preparation/source_item_view.html", context)

    def delete(self, request: HttpRequest, *, version: int) -> HttpResponse:
        """HTMX delete here will remove a source PDF file from the server.

        On success, this re-renders the particular card for this version.

        On error, typically b/c the files are in use, return an 409 and
        error message.
        """
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX DELETE requests are allowed")

        context = self.build_context()
        try:
            SourceService.delete_source_pdf(version)
        except PlomDependencyConflict as err:
            return HttpResponse(err, status=409)
        context.update({"src": SourceService.get_source_info(version)})
        return render(request, "Preparation/source_item_view.html", context)


class ReferenceImageView(ManagerRequiredView):
    def get(self, request: HttpRequest, *, version: int, page: int) -> HttpResponse:
        return FileResponse(SourceService._get_reference_image_file(version, page))
