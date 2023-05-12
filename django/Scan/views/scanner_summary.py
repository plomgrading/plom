# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ScannerRequiredView
from Scan.services import ScanService
from Progress.services import ManageScanService

from plom.misc_utils import format_int_list_with_runs


class ScannerSummaryView(ScannerRequiredView):
    """
    Display the summary of the whole test
    """

    def get(self, request):
        context = super().build_context()
        mss = ManageScanService()

        total_papers = mss.get_total_test_papers()
        complete_papers = mss.get_number_completed_test_papers()
        incomplete_papers = mss.get_number_incomplete_test_papers()

        unused_papers = mss.get_number_unused_test_papers()

        # this is a dict - key is paper_number, value = list of pages
        all_complete = mss.get_all_completed_test_papers()
        # turn into list of tuples (key, value) ordered by key
        all_complete_list = [(pn, pgs) for pn, pgs in sorted(all_complete.items())]

        # this is a dict - key is paper_number, value = list of pages
        all_incomplete = mss.get_all_incomplete_test_papers()
        # turn into list of tuples (key, value) ordered by key
        all_incomplete_list = [(pn, pgs) for pn, pgs in sorted(all_incomplete.items())]

        all_unused_list = format_int_list_with_runs(
            mss.get_all_unused_test_papers()
        ).split(",")

        context.update(
            {
                "complete_test_papers": complete_papers,
                "incomplete_test_papers": incomplete_papers,
                "unused_test_papers": unused_papers,
                "total_papers": total_papers,
                "all_complete_list": all_complete_list,
                "all_incomplete_list": all_incomplete_list,
                "all_unused_list": all_unused_list,
            }
        )

        return render(request, "Scan/summary_of_pushed.html", context)


class ScannerPushedImageView(ScannerRequiredView):
    """
    Display the summary of the whole test
    """

    def get(self, request, img_pk):
        mss = ManageScanService()
        img = mss.get_pushed_image(img_pk)
        return FileResponse(img.image_file)