# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.shortcuts import render

from Base.base_group_views import ScannerRequiredView
from Progress.services import ManageScanService

from plom.misc_utils import format_int_list_with_runs


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
        return render(request, "Scan/scan_incomplete.html", context)


class ScannerSummaryView(ScannerRequiredView):
    """Display the summary of the whole test."""

    def get(self, request: HttpRequest) -> HttpResponse:
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
    """Return a pushed image given by its pk."""

    def get(self, request: HttpRequest, *, img_pk: int) -> FileResponse:
        img = ManageScanService().get_pushed_image(img_pk)
        if img is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        return FileResponse(img.image_file)


class ScannerPushedImageWrapView(ScannerRequiredView):
    """Return the simple html wrapper around the pushed image with correct rotation."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        pushed_img = ManageScanService().get_pushed_image(img_pk)
        if pushed_img is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        pushed_img_page_info = ManageScanService().get_pushed_image_page_info(img_pk)
        # pass negative of angle for css rotation since it uses positive=clockwise (sigh)
        context = {
            "image_pk": img_pk,
            "angle": -pushed_img.rotation,
            "page_info": pushed_img_page_info,
        }
        return render(request, "Scan/fragments/pushed_image_wrapper.html", context)
