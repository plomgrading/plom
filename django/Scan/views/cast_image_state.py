# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechntizer

from django_htmx.http import HttpResponseClientRefresh
from django.shortcuts import render
from django.http import HttpResponse, Http404
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanCastService, ScanService
from Papers.services import SpecificationService


class DiscardImageType(ScannerRequiredView):
    """Discard a particular StagingImage type."""

    def post(self, request, timestamp, index):
        ScanCastService().discard_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()


class UnknowifyImageType(ScannerRequiredView):
    """Unknowify a particular StagingImage type."""

    def post(self, request, timestamp, index):
        ScanCastService().unknowify_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()


class KnowifyImageType(ScannerRequiredView):
    """Knowify a particular StagingImage type."""

    def get(self, request, timestamp, index):

        context = super().build_context()
        scanner = ScanService()
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

        print(">"*40, SpecificationService().get_n_to_produce())
        
        page_labels = [
                f"p.{n+1}" for n in range(SpecificationService().get_n_pages())
        ]
        paper_numbers = scanner.get_bundle_paper_numbers(bundle)
        all_paper_numbers = [
            n + 1 for n in range(SpecificationService().get_n_to_produce())
        ]
        context.update(
            {
                "page_labels": page_labels,
                "bundle_paper_numbers": paper_numbers,
                "all_paper_numbers": all_paper_numbers,
            }
        )

        return render(request, "Scan/fragments/knowify_image.html", context)


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

        if len(extra_page_data.get("pages", [])):
            page_list = [int(p) for p in extra_page_data["pages"]]
        else:
            return HttpResponse(
                """<span class="alert alert-danger">Exactly one page</span>"""
            )

        ###>>>> HERE ###

class ExtraliseImageType(ScannerRequiredView):
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
                n + 1 for n in range(SpecificationService().get_n_questions())
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
