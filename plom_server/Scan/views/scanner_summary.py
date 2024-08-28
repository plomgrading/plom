# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib import messages

from Base.base_group_views import ScannerRequiredView
from ..services import ManageScanService


class ScannerCompletePaperView(ScannerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        mss = ManageScanService()

        # this is a dict - key is paper_number, value = list of pages
        completed_papers_dict = mss.get_all_completed_test_papers()
        # turn into list of tuples (key, value) ordered by key
        completed_papers_list = [
            (pn, pgs) for pn, pgs in sorted(completed_papers_dict.items())
        ]

        context = self.build_context()
        context.update(
            {
                "current_page": "complete",
                "number_of_completed_papers": len(completed_papers_dict),
                "completed_papers_list": completed_papers_list,
            }
        )
        return render(request, "Scan/scan_complete.html", context)


class ScannerIncompletePaperView(ScannerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        mss = ManageScanService()

        # this is a dict - key is paper_number, value = list of pages
        incomplete_papers_dict = mss.get_all_incomplete_test_papers()
        # turn into list of tuples (key, value) ordered by key
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
