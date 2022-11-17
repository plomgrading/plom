# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse

from Base.base_group_views import ManagerRequiredView
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


class ErrorPagesModal(ManagerRequiredView):
    """
    Display the error page, and give manager different
    types of actions to resolve the error page.
    """
    def get(self, request, test_paper, page_number, hash):
        context = self.build_context()

        context.update({
            "test_paper": test_paper,
            "page_number": page_number,
            "error_hash": hash,
        })

        return render(request, "Progress/fragments/scan_error_modal.html", context)