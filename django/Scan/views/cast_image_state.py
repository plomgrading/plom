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
        ScanCastService().extralise_image_type_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()

    def delete(self, request, timestamp, index):
        ScanCastService().clear_extra_page_info_from_bundle_timestamp_and_order(
            request.user, timestamp, index
        )

        return HttpResponseClientRefresh()
