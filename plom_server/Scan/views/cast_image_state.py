# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechntizer

from django_htmx.http import HttpResponseClientRefresh
from django.shortcuts import render
from django.http import HttpResponse, Http404

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService, PaperInfoService

from ..services import ScanCastService, ScanService


class DiscardImageView(ScannerRequiredView):
    """Discard a particular StagingImage type."""

    def post(self, request, timestamp, index):
        ScanCastService().discard_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()


class UnknowifyImageView(ScannerRequiredView):
    """Unknowify a particular StagingImage type."""

    def post(self, request, timestamp, index):
        ScanCastService().unknowify_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()


class KnowifyImageView(ScannerRequiredView):
    """Knowify a particular StagingImage type."""

    def get(self, request, timestamp, index):
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "slug": bundle.slug,
                "timestamp": timestamp,
                "index": index,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
            }
        )

        page_labels = [f"page {n+1}" for n in range(SpecificationService.get_n_pages())]
        all_paper_numbers = paper_info.which_papers_in_database()
        missing_papers_pages = scanner.get_bundle_missing_paper_page_numbers(bundle)
        context.update(
            {
                "page_labels": page_labels,
                "all_paper_numbers": all_paper_numbers,
                "missing_papers_pages": missing_papers_pages,
            }
        )

        return render(request, "Scan/fragments/knowify_image.html", context)

    def post(self, request, timestamp, index):
        # TODO - improve this form processing

        knowify_page_data = request.POST

        if knowify_page_data.get("bundleOrArbitrary", "off") == "on":
            try:
                paper_number, page_number = knowify_page_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Choose paper/page</div>"""
                )
        else:
            paper_number = knowify_page_data.get("arbitraryPaper", None)

        try:
            paper_number = int(paper_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Invalid paper number</div>"""
            )

        try:
            page_number = int(page_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Select a page</div>"""
            )

        try:
            ScanCastService().knowify_image_from_bundle_timestamp_and_order(
                request.user, timestamp, index, paper_number, page_number
            )
        except ValueError as err:
            return HttpResponse(f"""<div class="alert alert-danger">{err}</div>""")

        return HttpResponseClientRefresh()


class ExtraliseImageView(ScannerRequiredView):
    """Extralise a particular StagingImage type."""

    def post(self, request, timestamp, index):
        # TODO - improve this form processing

        extra_page_data = request.POST

        if extra_page_data.get("bundleOrArbitrary", "off") == "on":
            paper_number = extra_page_data.get("bundlePaper", None)
        else:
            paper_number = extra_page_data.get("arbitraryPaper", None)

        try:
            paper_number = int(paper_number)
        except ValueError:
            return HttpResponse(
                """<span class="alert alert-danger">Invalid paper number</span>"""
            )

        if extra_page_data.get("questionAll", "off") == "all":
            # set all the questions
            question_list = [
                n + 1 for n in range(SpecificationService.get_n_questions())
            ]
        else:
            if len(extra_page_data.get("questions", [])):
                question_list = [int(q) for q in extra_page_data["questions"]]
            else:
                return HttpResponse(
                    """<span class="alert alert-danger">At least one question</span>"""
                )

        ScanCastService().assign_extra_page_from_bundle_timestamp_and_order(
            request.user, timestamp, index, paper_number, question_list
        )

        return HttpResponseClientRefresh()

    def put(self, request, timestamp, index):
        ScanCastService().extralise_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()

    def delete(self, request, timestamp, index):
        ScanCastService().clear_extra_page_info_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()
