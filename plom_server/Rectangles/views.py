# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from django.http import (
    HttpRequest,
    HttpResponse,
    FileResponse,
    Http404,
)
from django.core.files.base import ContentFile
from django.shortcuts import render

from Papers.services import SpecificationService, PaperInfoService
from Preparation.services import SourceService
from Base.base_group_views import ManagerRequiredView
from .services import get_reference_rectangle, RectangleExtractor


class RectangleHomeView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        context.update(
            {
                "num_versions": SpecificationService.get_n_versions(),
                "number_of_pages": SpecificationService.get_n_pages(),
                "uploaded_sources": SourceService.get_list_of_sources(),
                "version_list": SpecificationService.get_list_of_versions(),
                "page_list": SpecificationService.get_list_of_pages,
            }
        )
        return render(request, "Rectangles/home.html", context)


class SelectRectangleView(ManagerRequiredView):
    def get(self, request: HttpRequest, version: int, page: int) -> HttpResponse:
        context = self.build_context()
        try:
            qr_info = get_reference_rectangle(version, page)
        except ValueError as err:
            raise Http404(err)
        x_coords = [X[0] for X in qr_info.values()]
        y_coords = [X[1] for X in qr_info.values()]
        rect_top_left = [min(x_coords), min(y_coords)]
        rect_bottom_right = [max(x_coords), max(y_coords)]
        context.update(
            {
                "version": version,
                "page_number": page,
                "qr_info": qr_info,
                "top_left": rect_top_left,
                "bottom_right": rect_bottom_right,
            }
        )

        return render(request, "Rectangles/select.html", context)

    def post(self, request: HttpRequest, version: int, page: int) -> HttpResponse:
        context = self.build_context()
        left = round(float(request.POST.get("plom_left")), 6)
        top = round(float(request.POST.get("plom_top")), 6)
        right = round(float(request.POST.get("plom_right")), 6)
        bottom = round(float(request.POST.get("plom_bottom")), 6)
        # get all scanned papers with that page,version
        paper_numbers = (
            PaperInfoService().get_paper_numbers_containing_given_page_version(
                version, page, scanned=True
            )
        )
        context.update(
            {
                "version": version,
                "page_number": page,
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "papers": paper_numbers,
            }
        )
        return render(request, "Rectangles/show_rectangles.html", context)


class ExtractedRectangleView(ManagerRequiredView):
    def get(
        self, request: HttpRequest, paper: int, version: int, page: int
    ) -> HttpResponse:
        try:
            rex = RectangleExtractor(version, page)
        except ValueError as err:
            raise Http404(err)

        left = float(request.GET.get("left"))
        right = float(request.GET.get("right"))
        top = float(request.GET.get("top"))
        bottom = float(request.GET.get("bottom"))

        rect_region_bytes = rex.extract_rect_region(paper, left, top, right, bottom)
        if rect_region_bytes is None:
            # TODO - correctly handle the None-return case when
            # rex cannot compute appropriate transforms.
            raise Http404("Could not extract")
        return FileResponse(ContentFile(rect_region_bytes))


class ZipExtractedRectangleView(ManagerRequiredView):
    def get(self, request: HttpRequest, version: int, page: int) -> HttpResponse:
        try:
            rex = RectangleExtractor(version, page)
        except ValueError as err:
            raise Http404(err)

        left = float(request.GET.get("left"))
        right = float(request.GET.get("right"))
        top = float(request.GET.get("top"))
        bottom = float(request.GET.get("bottom"))

        tmpzip = NamedTemporaryFile(delete=False)
        try:
            rex.build_zipfile(tmpzip.name, left, top, right, bottom)

            return FileResponse(
                tmpzip, filename=f"extracted_rectangles_v{version}_pg{page}.zip"
            )
        finally:
            Path(tmpzip.name).unlink()
