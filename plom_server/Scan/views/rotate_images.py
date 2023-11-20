# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer


from io import BytesIO
from PIL import Image

from django.http import Http404, FileResponse, HttpResponse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from ..services import ImageRotateService, ScanService


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
        if theta is None or theta == 0:
            return FileResponse(img_obj.image_file)
        else:
            fh = BytesIO()
            with Image.open(img_obj.image_file) as tmp_img:
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
                tmp_img.rotate(theta, expand=True).save(fh, "png")
                return HttpResponse(fh.getvalue(), content_type="image/png")


class GetRotatedThumbnailView(ScannerRequiredView):
    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        img_obj = scanner.get_thumbnail_image(timestamp, request.user, index)

        theta = img_obj.staging_image.rotation
        if theta is None or theta == 0:
            return FileResponse(img_obj.image_file)
        else:
            fh = BytesIO()
            with Image.open(img_obj.image_file) as tmp_img:
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
                tmp_img.rotate(theta, expand=True).save(fh, "png")
                return HttpResponse(fh.getvalue(), content_type="image/png")
