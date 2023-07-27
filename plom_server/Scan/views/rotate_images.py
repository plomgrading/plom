# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from ..services import ImageRotateService


class RotateImageClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(
            request.user, timestamp, index, angle=-90
        )

        return HttpResponseClientRefresh()


class RotateImageCounterClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(
            request.user, timestamp, index, angle=90
        )

        return HttpResponseClientRefresh()
