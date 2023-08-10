# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse
from django.http import HttpResponse


from Papers.services import SpecificationService
from Progress.services import ManageScanService, ManageDiscardService
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

        papers_missing_fixed_pages = mss.get_papers_missing_fixed_pages()
        question_labels = [
            f"Q.{n+1}" for n in range(SpecificationService.get_n_questions())
        ]
        used_papers = mss.get_all_used_test_papers()

        context.update(
            {
                "papers_missing_fixed_pages": papers_missing_fixed_pages,
                "question_labels": question_labels,
                "used_papers": used_papers,
            }
        )

        return render(request, "Progress/scan_reassign.html", context)

    def post(self, request, img_pk):
        reassignment_data = request.POST
        mds = ManageDiscardService()

        if reassignment_data.get("assignment_type", "fixed") == "fixed":
            try:
                paper_number, page_number = reassignment_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Choose paper/page</div>"""
                )
            try:
                mds.assign_discard_image_to_fixed_page(
                    request.user, img_pk, paper_number, page_number
                )
            except ValueError as e:
                return HttpResponse(
                    f"""<span class="alert alert-danger">Some sort of error: {e}</span>"""
                )
        else:
            paper_number = reassignment_data.get("usedPaper", None)

            try:
                paper_number = int(paper_number)
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Invalid paper number</div>"""
                )
            if reassignment_data.get("questionAll", "off") == "all":
                # set all the questions
                question_list = [
                    n + 1 for n in range(SpecificationService.get_n_questions())
                ]
            else:
                if len(reassignment_data.get("questions", [])):
                    question_list = [int(q) for q in reassignment_data["questions"]]
                else:
                    return HttpResponse(
                        """<span class="alert alert-danger">At least one question</span>"""
                    )
            try:
                mds.assign_discard_image_to_mobile_page(
                    request.user, img_pk, paper_number, question_list
                )
            except ValueError as e:
                return HttpResponse(
                    f"""<span class="alert alert-danger">Some sort of error: {e}</span>"""
                )

        return HttpResponseClientRedirect(reverse("progress_scan_discard"))
