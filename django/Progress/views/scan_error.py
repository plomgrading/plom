# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse

from Progress.views import BaseScanProgressPage
from Progress.services import ManageScanService


class ScanError(BaseScanProgressPage):
    """
    View and manage error pages.
    """

    def get(self, request):
        context = self.build_context("error_page")
        mss = ManageScanService()
        error_pages = mss.get_error_pages_list()
        context.update({"error_pages": error_pages, "n_errors": len(error_pages)})
        return render(request, "Progress/scan_error.html", context)