# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.shortcuts import render

from Progress.services import ManageScanService
from Progress.views import BaseScanProgressPage


class ScanDiscardView(BaseScanProgressPage):
    """View the table of discarded images."""

    def get(self, request):
        mss = ManageScanService()
        context = self.build_context("discard")
        discards = mss.get_discarded_images()
        context.update({"number_of_discards": len(discards), "discards": discards})
        return render(request, "Progress/scan_discard.html", context)


class ScanReassignView(BaseScanProgressPage):
    def get(self, request):
        context = self.build_context("discard")
        return render(request, "Progress/scan_discard.html", context)
