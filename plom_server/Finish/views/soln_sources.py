# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025-2026 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    FileResponse,
    Http404,
    HttpResponseBadRequest,
)
from django.shortcuts import render
from django.urls import reverse

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SolnSpecService
from ..services import SolnSourceService, BuildSolutionService


class SolnSourcesView(ManagerRequiredView):
    """View to provide access to the source PDFs."""

    def get(
        self, request: HttpRequest, *, version: int | None = None
    ) -> HttpResponse | FileResponse:
        """Get either a particular version PDF or a rendered HTML page about all versions."""
        context = self.build_context()
        if not SolnSpecService.is_there_a_soln_spec():
            return HttpResponseRedirect(reverse("soln_home"))

        # version is non-null when user wants to download the source.
        if version:
            try:
                source_bytes = SolnSourceService.get_soln_pdf_for_download(version)
                return FileResponse(
                    source_bytes,
                    as_attachment=True,
                    filename=f"solution{version}.pdf",
                )
            except ObjectDoesNotExist:
                raise Http404("No such file")

        solns = SolnSourceService.get_list_of_sources()
        hashes = [s["hash"] for s in solns if s["uploaded"]]
        if len(hashes) != len(set(hashes)):
            dupes_warning = True
        else:
            dupes_warning = False

        context.update(
            {
                "soln_sources": solns,
                "dupes_warning": dupes_warning,
            }
        )
        return render(request, "Finish/soln_sources.html", context)

    def post(self, request: HttpRequest, *, version: int | None = None) -> HttpResponse:
        """HTMX posts here will add a new solution PDF file to the server.

        On success, this re-renders the particular card for this version.
        TODO: on failure, does stuff with errors-as-success: consider porting to
        hx-error as in other places; do it for source updates as well.
        """
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX POST requests are allowed")

        if not version:
            return HttpResponseBadRequest("Only supports uploading by version")

        if not request.FILES["soln_pdf"]:
            return HttpResponseBadRequest("Must include a 'soln_pdf' field")

        context = self.build_context()
        try:
            SolnSourceService.take_solution_source_pdf_from_upload(
                version, request.FILES["soln_pdf"]
            )
            context["error"] = False
            context["message"] = ""
        except ValueError as err:
            context["error"] = True
            context["message"] = f"{err}"
        context.update({"soln": SolnSourceService.get_source_info(version)})
        return render(request, "Finish/soln_item_view.html", context)

    def delete(
        self, request: HttpRequest, *, version: int | None = None
    ) -> HttpResponse:
        """HTMX delete here to delete this soln source pdf (and reset any built soln pdfs).

        On success, this re-renders the particular card for this version.
        Currently the only failures are from misuse: none of the work here is expected
        to fail.
        TODO: despite no errors expected, consider porting to hx-error as in other
        places; do it for source updates as well.
        """
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX DELETE requests are allowed")

        if not version:
            return HttpResponseBadRequest("Only supports deleting a particular version")

        context = self.build_context()
        BuildSolutionService.reset_all_soln_build()
        SolnSourceService.remove_solution_pdf(version)
        context.update({"soln": SolnSourceService.get_source_info(version)})
        return render(request, "Finish/soln_item_view.html", context)
