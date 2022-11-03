# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.shortcuts import render

from Progress.services import ManageScanService
from Base.base_group_views import ManagerRequiredView


class BaseScanProgressPage(ManagerRequiredView):
    """
    Base view for each of the "tabs" in the scanning progress card.
    """

    def build_context(self, page_name):
        """
        page_name (str): name of the current page, for coloring in the active tab
        """

        context = super().build_context()
        context.update({"curr_page": page_name})
        return context


class ScanOverview(BaseScanProgressPage):
    """
    View the progress of scanning/validating page-images.
    """

    def get(self, request):
        mss = ManageScanService()
        total_pages = mss.get_total_pages()
        scanned_pages = mss.get_scanned_pages()
        percent_pages_complete = scanned_pages / total_pages * 100

        total_papers = mss.get_total_test_papers()
        completed_papers = mss.get_completed_test_papers()
        percent_papers_complete = completed_papers / total_papers * 100

        context = self.build_context("overview")
        context.update(
            {
                "total_pages": total_pages,
                "scanned_pages": scanned_pages,
                "percent_pages_complete": int(percent_pages_complete),
                "total_papers": total_papers,
                "completed_papers": completed_papers,
                "percent_papers_complete": int(percent_papers_complete),
                "test_papers": mss.get_test_paper_list(),
            }
        )
        return render(request, "Progress/scan_overview.html", context)


class ScanBundles(BaseScanProgressPage):
    """
    View the bundles uploaded by scanner users.
    """

    def get(self, request):
        context = self.build_context("bundles")
        return render(request, "Progress/scan_bundles.html", context)


class ScanColliding(BaseScanProgressPage):
    """
    View and manage colliding pages.
    """

    def get(self, request):
        context = self.build_context("colliding")
        return render(request, "Progress/scan_collide.html", context)


class ScanUnknown(BaseScanProgressPage):
    """
    View and manage unknown pages.
    """

    def get(self, request):
        context = self.build_context("unknown_page")
        return render(request, "Progress/scan_unknown.html", context)


class ScanError(BaseScanProgressPage):
    """
    View and manage error pages.
    """

    def get(self, request):
        context = self.build_context("error_page")
        return render(request, "Progress/scan_error.html", context)


class ScanExtra(BaseScanProgressPage):
    """
    View and manage extra pages.
    """

    def get(self, request):
        context = self.build_context("extra")
        return render(request, "Progress/scan_extra.html", context)


class ScanDiscarded(BaseScanProgressPage):
    """
    View and manage discarded pages.
    """

    def get(self, request):
        context = self.build_context("discarded")
        return render(request, "Progress/scan_discarded.html", context)
