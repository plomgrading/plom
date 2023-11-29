# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from django.urls import reverse
from django.http import Http404, HttpResponse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ScannerRequiredView

from ..services import (
    ImageRotateService,
    ScanService,
    hard_rotate_image_from_file_by_exif_and_angle,
)
from Progress.services import ManageScanService


class RotateImageClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(
            request.user, timestamp, index, angle=-90
        )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[timestamp]) + f"?pop={index}"
        )


class RotateImageCounterClockwise(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(
            request.user, timestamp, index, angle=90
        )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[timestamp]) + f"?pop={index}"
        )


class RotateImageOneEighty(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        ImageRotateService().rotate_image_from_bundle_timestamp_and_order(
            request.user, timestamp, index, angle=180
        )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[timestamp]) + f"?pop={index}"
        )


class GetRotatedBundleImageView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        img_obj = scanner.get_image(timestamp, request.user, index)

        theta = img_obj.rotation
        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.image_file, theta=theta
            ),
            content_type="image/png",
        )


class GetRotatedPushedImageView(ScannerRequiredView):
    """Return an image from a pushed bundle."""

    def get(self, request, img_pk):
        img_obj = ManageScanService().get_pushed_image(img_pk)

        theta = img_obj.rotation
        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.image_file, theta=theta
            ),
            content_type="image/png",
        )
