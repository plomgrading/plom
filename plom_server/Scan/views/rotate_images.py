# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from django.urls import reverse
from django.http import HttpResponse, HttpRequest, Http404
from django_htmx.http import HttpResponseClientRedirect

from plom_server.Base.base_group_views import ScannerRequiredView

from ..services import (
    ImageRotateService,
    ScanService,
    hard_rotate_image_from_file_by_exif_and_angle,
    ManageScanService,
)

from plom.plom_exceptions import PlomBundleLockedException


class RotateImageClockwise(ScannerRequiredView):
    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ImageRotateService().rotate_image_from_bundle_pk_and_order(
                bundle_id, index, angle=-90
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class RotateImageCounterClockwise(ScannerRequiredView):
    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ImageRotateService().rotate_image_from_bundle_pk_and_order(
                bundle_id, index, angle=90
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class RotateImageOneEighty(ScannerRequiredView):
    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ImageRotateService().rotate_image_from_bundle_pk_and_order(
                bundle_id, index, angle=180
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class GetRotatedBundleImageView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        scanner = ScanService()
        img_obj = scanner.get_image(bundle_id, index)

        theta = img_obj.rotation
        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.baseimage.image_file, theta=theta
            ),
            content_type="image/png",
        )


class GetRotatedPushedImageView(ScannerRequiredView):
    """Return an image from a pushed bundle."""

    def get(self, request: HttpRequest, img_pk: int) -> HttpResponse:
        img_obj = ManageScanService().get_pushed_image(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")

        theta = img_obj.rotation
        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.image_file, theta=theta
            ),
            content_type="image/png",
        )
