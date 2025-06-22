# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer

from django.urls import reverse
from django.shortcuts import render
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

from datetime import datetime


class RotateImageView(ScannerRequiredView):
    """Various operations related to rotated staged images."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Get a scanned page with server stored rotation applied."""
        img_obj = ScanService().get_image(bundle_id, index)

        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.baseimage.image_file, theta=img_obj.rotation
            ),
            content_type="image/png",
        )

    def post(
        self, request: HttpRequest, *, bundle_id: int, index: int, rotation: int
    ) -> HttpResponse:
        """Change the rotation on an image in a staged bundle.

        The rotation is in degrees, positive in the counterclockwise direction.
        TODO: For convenience with htmx this renders an html img element.
        """
        try:
            ImageRotateService().rotate_image_from_bundle_pk_and_order(
                bundle_id, index, angle=rotation
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        # TODO: this whole thing is clunky, probably easier to just return the image and update DOM via js
        return render(
            request,
            "Scan/fragments/bundle_page_img_tag.html",
            # we are using htmx to dynamically replace an existing image tag
            # if the new img tag uses the same src as the old one, the browser will load the cached image.
            # Append the _ts to force the browser to reload the image
            {
                "image": reverse("scan_get_rotated_image", args=[bundle_id, index])
                + f"?_ts={datetime.now().timestamp()}"
            },
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
                img_obj.baseimage.image_file, theta=theta
            ),
            content_type="image/png",
        )
