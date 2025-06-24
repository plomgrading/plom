# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

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

from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Preparation.services import SourceService
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Rectangles.services import get_reference_qr_coords_for_page


class QuestionClusteringHomeView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        context.update(
            {
                "version_list": SpecificationService.get_list_of_versions(),
                "q_idx_label_pairs": SpecificationService.get_question_index_label_pairs(),
                "q_idx_to_pages": SpecificationService.get_question_pages(),
            }
        )
        return render(request, "QuestionClustering/home.html", context)


class SelectRectangleForClusteringView(ManagerRequiredView):
    def get(
        self, request: HttpRequest, version: int, qidx: int, page: int
    ) -> HttpResponse:
        context = self.build_context()
        try:
            qr_info = get_reference_qr_coords_for_page(page, version=version)
        except ValueError as err:
            raise Http404(err) from err
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
                "q_label": SpecificationService.get_question_label(qidx),
            }
        )

        return render(request, "QuestionClustering/select.html", context)

    def post(
        self, request: HttpRequest, version: int, qidx: int, page: int
    ) -> HttpResponse:
        context = self.build_context()
        left = round(float(request.POST.get("plom_left")), 6)
        top = round(float(request.POST.get("plom_top")), 6)
        right = round(float(request.POST.get("plom_right")), 6)
        bottom = round(float(request.POST.get("plom_bottom")), 6)

        # get all scanned papers with that page,version
        # paper_numbers may be duplicated if there are multiple questions on a page
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page, version=version, scanned=True, limit=4
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
        return render(request, "QuestionClustering/show_rectangles.html", context)


class QuestionClusteringJobsHome(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        context.update(
            {
                "version_list": SpecificationService.get_list_of_versions(),
                "q_idx_label_pairs": SpecificationService.get_question_index_label_pairs(),
                "q_idx_to_pages": SpecificationService.get_question_pages(),
            }
        )
        return render(request, "QuestionClustering/clustering_jobs.html", context)
