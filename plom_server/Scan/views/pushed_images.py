# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import FileResponse, HttpRequest, HttpResponse, Http404
from django_htmx.http import HttpResponseClientRefresh
from django.contrib import messages

from Base.base_group_views import ScannerLeadMarkerOrManagerView
from ..services import (
    hard_rotate_image_from_file_by_exif_and_angle,
    ForgiveMissingService,
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

    def get(
        self, request: HttpRequest, *, page_kind: str, page_pk: int
    ) -> HttpResponse:
        mss = ManageScanService()
        if page_kind == "fixed":
            pushed_page_info = mss.get_pushed_fixed_page_image_info(page_pk)
        elif page_kind == "mobile":
            pushed_page_info = mss.get_pushed_mobile_page_image_info(page_pk)
        elif page_kind == "discard":
            pushed_page_info = mss.get_pushed_discard_page_image_info(page_pk)
        else:
            raise Http404(
                f"Cannot find pushed image of kind {page_kind} and page_pk {page_pk}."
            )
        img_pk = pushed_page_info["image_pk"]
        pushed_img = mss.get_pushed_image(img_pk)
        if pushed_img is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")

        context = {
            "image_pk": img_pk,
            # pass negative of angle for css rotation since it uses positive=clockwise (sigh)
            "angle": -pushed_img.rotation,
            "page_info": pushed_page_info,
            "page_pk": page_pk,
        }

        return render(request, "Scan/fragments/pushed_image_wrapper.html", context)


class SubstituteImageWrapView(ScannerLeadMarkerOrManagerView):
    """Return the simple html wrapper around the substitute forgive image."""

    def get(self, request: HttpRequest, *, paper: int, page: int) -> HttpResponse:
        pg_info = ForgiveMissingService.get_substitute_page_info(paper, page)
        context = {
            "paper_number": pg_info["paper_number"],
            "page_number": pg_info["page_number"],
            "version": pg_info["version"],
            "kind": pg_info["kind"],
            "substitute_image_pk": pg_info["substitute_image_pk"],
        }

        return render(request, "Scan/fragments/substitute_image_wrapper.html", context)

    def post(self, request: HttpRequest, *, paper: int, page: int) -> HttpResponse:
        """Replace the missing page from the given paper."""
        try:
            ForgiveMissingService.forgive_missing_fixed_page(request.user, paper, page)
        except (ObjectDoesNotExist, ValueError) as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRefresh()
        # if everything succeeds then refresh the page.
        return HttpResponseClientRefresh()


class SubstituteImageView(ScannerLeadMarkerOrManagerView):
    """Return a substitute image given by its pk."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        img_obj = ForgiveMissingService.get_substitute_image_from_pk(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        return FileResponse(img_obj.image_file)
