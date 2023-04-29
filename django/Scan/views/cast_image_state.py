# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanCastService, ScanService


class DiscardImageType(ScannerRequiredView):
    """
    Discard a particular StagingImage type.
    """

    def post(self, request, timestamp, index):
        user_obj = request.user
        bundle_obj = ScanService().get_bundle_from_timestamp(timestamp)
        img_obj = ScanService().get_img_obj(bundle_obj, index)
        ScanCastService().discard_image_type_from_bundle(
            user_obj, bundle_obj, index, img_obj.image_type
        )

        return HttpResponseClientRefresh()
