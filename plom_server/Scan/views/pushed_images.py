# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.shortcuts import render
from django.http import FileResponse, HttpRequest, HttpResponse, Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerLeadMarkerOrManagerView
from ..services import (
    hard_rotate_image_from_file_by_exif_and_angle,
    ManageScanService,
    ManageDiscardService,
)


class PushedImageView(ScannerLeadMarkerOrManagerView):
    """Get or delete a pushed image by specifying its primary key."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        """Return a pushed image by its primary."""
        img_obj = ManageScanService().get_pushed_image(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        return FileResponse(img_obj.image_file)

    def delete(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        """Discard a pushed image by its primary key."""
        mds = ManageDiscardService()
        mds.discard_pushed_image_from_pk(request.user, img_pk)
        return HttpResponseClientRefresh()


class PushedImageRotatedView(ScannerLeadMarkerOrManagerView):
    """Return a pushed image given by its pk, pass back hard rotated image."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        img_obj = ManageScanService().get_pushed_image(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")

        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.image_file, theta=img_obj.rotation
            ),
            content_type="image/png",
        )


class PushedImageWrapView(ScannerLeadMarkerOrManagerView):
    """Return the simple html wrapper around the pushed image with correct rotation."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        mss = ManageScanService()
        pushed_img = mss.get_pushed_image(img_pk)
        if pushed_img is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        pushed_img_page_info = mss.get_pushed_image_page_info(img_pk)

        # pass negative of angle for css rotation since it uses positive=clockwise (sigh)
        context = {
            "image_pk": img_pk,
            "angle": -pushed_img.rotation,
            "page_info": pushed_img_page_info,
        }

        return render(request, "Scan/fragments/pushed_image_wrapper.html", context)
