# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse


from plom_server.Base.base_group_views import ManagerRequiredView, ScannerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import ManageScanService, ManageDiscardService


class ScannerDiscardView(ScannerRequiredView):
    """View the table of discarded images."""

    def get(self, request: HttpRequest) -> HttpResponse:
        mss = ManageScanService()
        context = self.build_context()
        discards = mss.get_discarded_page_info()
        context.update(
            {
                "current_page": "discard",
                "number_of_discards": len(discards),
                "discards": discards,
            }
        )
        return render(request, "Scan/scan_discard.html", context)


class ScannerReassignView(ManagerRequiredView):
    def get(self, request: HttpRequest, *, page_pk: int) -> HttpResponse:
        mss = ManageScanService()
        discard_page_info = mss.get_pushed_discard_page_image_info(page_pk)
        img_pk = discard_page_info["image_pk"]
        tmp = mss.get_pushed_image(img_pk)
        if tmp is None:
            return Http404(f"Unexpected could not find pushed image with pk {img_pk}")
        img_angle = -tmp.rotation
        context = self.build_context()
        context.update(
            {
                "page_pk": page_pk,
                "current_page": "reassign",
                "image_pk": img_pk,
                "angle": img_angle,
            }
        )

        papers_missing_fixed_pages = mss.get_papers_missing_fixed_pages()
        used_papers = ManageScanService.get_all_used_papers()
        question_labels_html = SpecificationService.get_question_html_label_triples()

        context.update(
            {
                "papers_missing_fixed_pages": papers_missing_fixed_pages,
                "question_labels_html": question_labels_html,
                "used_papers": used_papers,
            }
        )

        return render(request, "Scan/reassign_discard.html", context)

    def post(self, request: HttpRequest, *, page_pk: int) -> HttpResponse:
        reassignment_data = request.POST

        if reassignment_data.get("assignment_type", "fixed") == "fixed":
            try:
                paper_number, page_number = reassignment_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<span class="alert alert-danger">Choose paper/page</span>"""
                )
            try:
                ManageDiscardService().assign_discard_page_to_fixed_page(
                    request.user, page_pk, paper_number, page_number
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
                    """<span class="alert alert-danger">Invalid paper number</span>"""
                )

            choice = reassignment_data.get("question_all_dnm", "")
            if choice == "choose_all":
                # set all the questions
                to_questions = SpecificationService.get_question_indices()
            elif choice == "choose_dnm":
                # TODO: or explicitly empty list or ...?
                to_questions = []
            elif choice == "choose_q":
                # caution: `get` would return just the last entry
                to_questions = [int(q) for q in reassignment_data.getlist("questions")]
                if not to_questions:
                    return HttpResponse(
                        """<span class="alert alert-danger">At least one question</span>"""
                    )
            else:
                return HttpResponse(
                    """<span class="alert alert-danger">
                        Unexpected radio choice: this is a bug; please file an issue!
                    </span>"""
                )

            try:
                ManageDiscardService()._assign_discard_page_to_mobile_page(
                    page_pk, paper_number, to_questions
                )
            except ValueError as e:
                return HttpResponse(
                    f"""<span class="alert alert-danger">Some sort of error: {e}</span>"""
                )

        return HttpResponseClientRedirect(reverse("scan_list_discard"))
