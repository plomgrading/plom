# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechntizer

from django_htmx.http import HttpResponseClientRefresh
from django.http import HttpResponse
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanCastService
from Papers.services import SpecificationService


class DiscardImageType(ScannerRequiredView):
    """
    Discard a particular StagingImage type.
    """

    def post(self, request, timestamp, index):
        ScanCastService().discard_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()


class ExtraliseImageType(ScannerRequiredView):
    """
    Extralise a particular StagingImage type.
    """

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
