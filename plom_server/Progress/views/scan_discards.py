# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.shortcuts import render

from Papers.services import PaperInfoService, SpecificationService
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
    def get(self, request, img_pk):
        mss = ManageScanService()
        img_angle = -mss.get_pushed_image(img_pk).rotation
        context = self.build_context("reassign")
        context.update({"image_pk": img_pk, "angle": img_angle})

        paper_info = PaperInfoService()
        all_paper_numbers = paper_info.which_papers_in_database()
        papers_missing_fixed_pages = mss.get_papers_missing_fixed_pages()
        specinfo = SpecificationService()
        page_labels = [f"page {n+1}" for n in range(specinfo.get_n_pages())]
        question_labels = [f"Q.{n+1}" for n in range(specinfo.get_n_questions())]
        used_papers = mss.get_all_used_test_papers()
        context.update(
            {
                "all_paper_numbers": all_paper_numbers,
                "papers_missing_fixed_pages": papers_missing_fixed_pages,
                "page_labels": page_labels,
                "question_labels": question_labels,
                "used_papers": used_papers,
            }
        )

        return render(request, "Progress/scan_reassign.html", context)
