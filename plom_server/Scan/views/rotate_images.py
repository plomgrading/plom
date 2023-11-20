# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer


from io import BytesIO
from PIL import Image

from django.http import Http404, HttpResponse, FileResponse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from ..services import ImageRotateService, ScanService
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


def hard_rotate_image_by_exif_and_angle(image_file, theta=None):
    if theta is None:
        theta = 0
    with Image.open(image_file) as tmp_img:
        exif_orient = tmp_img.getexif().get(274, 1)
        if exif_orient == 1:
            pass
        elif exif_orient == 3:
            theta += 180
        elif exif_orient == 6:
            theta -= 90
        elif exif_orient == 8:
            theta += 90
        else:
            raise ValueError(
                f"Do not recognise this exif orientation value {exif_orient}"
            )
        fh = BytesIO()
        # rotate the and return it.
        # TODO - optimise the total-angle-zero case?
        tmp_img.rotate(theta, expand=True).save(fh, "png")
        return HttpResponse(fh.getvalue(), content_type="image/png")


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
        return hard_rotate_image_by_exif_and_angle(img_obj.image_file, theta)


class GetRotatedThumbnailView(ScannerRequiredView):
    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        img_obj = scanner.get_thumbnail_image(timestamp, request.user, index)

        # get rotation angle from the parent staging image.
        theta = img_obj.staging_image.rotation
        return hard_rotate_image_by_exif_and_angle(img_obj.image_file, theta)


class GetRotatedPushedImageView(ScannerRequiredView):
    """Return an image from a pushed bundle."""

    def get(self, request, img_pk):
        img_obj = ManageScanService().get_pushed_image(img_pk)

        theta = img_obj.rotation
        return hard_rotate_image_by_exif_and_angle(img_obj.image_file, theta)
