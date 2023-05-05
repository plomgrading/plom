# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechntizer

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanCastService


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
        # TODO - decrapify this form processing

        extra_page_data = request.POST
        print(">" * 20, extra_page_data)
        if extra_page_data.get("bundleOrArbitrary", "off") == "on":
            paper_number = extra_page_data.get("bundlePaper", None)
        else:
            paper_number = extra_page_data.get("arbitraryPaper", None)
        if paper_number.isnumeric():
            paper_number = int(paper_number)
            print(f"Set to paper_number {paper_number}")
        else:
            # invalid paper number
            print(f"Invalid paper_number {paper_number}")
            return HttpResponseClientRefresh()

        if extra_page_data.get("questionAll", "off") == "all":
            print("Set all question")
        else:
            pass

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
