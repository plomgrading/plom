# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from Scan.services import ImageRotateService

class RotateImageClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(request.user, timestamp, index, clockwise=True, counter_clockwise=False)

        return HttpResponseClientRefresh()


class RotateImageCounterClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(request.user, timestamp, index, clockwise=False, counter_clockwise=True)

        return HttpResponseClientRefresh()
