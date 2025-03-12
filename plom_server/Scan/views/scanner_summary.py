# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib import messages

from plom_server.Base.base_group_views import ScannerRequiredView
from ..services import ManageScanService


class ScannerCompletePaperView(ScannerRequiredView):
    """View for Complete Scans page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render a page of information about scans that are complete."""
        # dict keyed by paper_number, contents a bit complicated
        complete_papers_dict = ManageScanService.get_all_complete_papers()
        # turn into list of tuples (papernum, value) ordered by papernum
        complete_papers_list = [
            (pn, pgs) for pn, pgs in sorted(complete_papers_dict.items())
        ]

        context = self.build_context()
        context.update(
            {
                "current_page": "complete",
                "number_of_complete_papers": len(complete_papers_dict),
                "complete_papers_list": complete_papers_list,
            }
        )
        return render(request, "Scan/scan_complete.html", context)


class ScannerIncompletePaperView(ScannerRequiredView):
    """View for Incomplete Scans page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render a page of information about scans that are incomplete."""
        # dict keyed by paper_number, contents a bit complicated
        incomplete_papers_dict = ManageScanService.get_all_incomplete_papers()
        # turn into list of tuples (papernum, value) ordered by papernum
        incomplete_papers_list = [
            (pn, pgs) for pn, pgs in sorted(incomplete_papers_dict.items())
        ]

        context = self.build_context()
        context.update(
            {
                "current_page": "incomplete",
                "number_of_incomplete_papers": len(incomplete_papers_dict),
                "incomplete_papers_list": incomplete_papers_list,
            }
        )
        # display any errors for an attempted missing page forgive.
        forgive_errors = []
        for msg in messages.get_messages(request):
            forgive_errors.append(f"{msg}")
        context.update({"forgive_errors": forgive_errors})
        return render(request, "Scan/scan_incomplete.html", context)
