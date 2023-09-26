# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Progress.services import ManageScanService


class ScanIncompleteView(ManagerRequiredView):
    """View the table of complete pushed papers."""

    def get(self, request):
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
        return render(request, "Progress/scan_incomplete.html", context)
