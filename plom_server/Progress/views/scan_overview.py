# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Progress.services import ManageScanService


class ScanOverview(ManagerRequiredView):
    """View the progress of scanning/validating page-images."""

    def get(self, request):
        mss = ManageScanService()

        total_papers = mss.get_total_test_papers()
        completed_papers = mss.get_number_completed_test_papers()
        incomplete_papers = mss.get_number_incomplete_test_papers()
        pushed_bundles = mss.get_number_pushed_bundles()
        unpushed_bundles = mss.get_number_unpushed_bundles()

        context = self.build_context()
        context.update(
            {
                "current_page": "overview",
                "total_papers": total_papers,
                "completed_papers": completed_papers,
                "incomplete_papers": incomplete_papers,
                "pushed_bundles": pushed_bundles,
                "unpushed_bundles": unpushed_bundles,
            }
        )
        return render(request, "Progress/scan_overview.html", context)


class ScanBundlesView(ManagerRequiredView):
    """View the bundles uploaded by scanner users."""

    def get(self, request):
        context = self.build_context()
        mss = ManageScanService()

        bundle_list = mss.get_pushed_bundles_list()

        context.update(
            {
                "current_page": "bundles",
                "number_of_pushed_bundles": len(bundle_list),
                "pushed_bundles": bundle_list,
            }
        )
        return render(request, "Progress/scan_bundles.html", context)
