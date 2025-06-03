# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2025 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import FileResponse, HttpRequest, HttpResponse, Http404
from django_htmx.http import HttpResponseClientRefresh
from django.contrib import messages

from plom_server.Base.base_group_views import ScannerLeadMarkerOrManagerView
from plom_server.Finish.services import ReassembleService
from plom_server.Papers.services import SpecificationService
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
        return FileResponse(img_obj.baseimage.image_file)

    def delete(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        """Discard a pushed image by its primary key."""
        mds = ManageDiscardService()
        mds.discard_pushed_image_from_pk(request.user, img_pk)
        return HttpResponseClientRefresh()


class WholePaperView(ScannerLeadMarkerOrManagerView):
    """Perform operations on all images of a given paper."""

    def get(self, request: HttpRequest, *, paper_number: int) -> FileResponse:
        """Get an unmarked paper."""
        pdf_bytestream = ReassembleService().get_unmarked_paper(paper_number)

        shortname = SpecificationService.get_shortname()

        return FileResponse(
            pdf_bytestream,
            as_attachment=True,
            content_type="application/pdf",
            filename=f"{shortname}_{paper_number}.pdf",
        )

    def delete(self, request: HttpRequest, *, paper_number: int) -> HttpResponse:
        """Discard a whole paper by its paper number."""
        mds = ManageDiscardService()
        mds.discard_whole_paper_by_number(request.user, paper_number, dry_run=False)
        return HttpResponseClientRefresh()


class PushedImageRotatedView(ScannerLeadMarkerOrManagerView):
    """Return a pushed image given by its pk, pass back hard rotated image."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        img_obj = ManageScanService().get_pushed_image(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")

        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.baseimage.image_file, theta=img_obj.rotation
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
            # TODO: Issue #3591: who is consuming these messages?  Seems not the GET above
            # TODO: while addresses that, perhaps this post's docstring can say if this is
            return HttpResponseClientRefresh()
        # TODO: can we improve the below comment with what "the page" is?  Does it refer to
        # the "get" about 20 lines above here?
        # if everything succeeds then refresh the page.
        return HttpResponseClientRefresh()


class SubstituteImageView(ScannerLeadMarkerOrManagerView):
    """Return a substitute image given by its pk."""

    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        img_obj = ForgiveMissingService.get_substitute_image_from_pk(img_pk)
        if img_obj is None:
            raise Http404(f"Cannot find pushed image with pk {img_pk}.")
        return FileResponse(img_obj.baseimage.image_file)
