# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer


from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.shortcuts import render
from Papers.services import SpecificationService
from Preparation.services import SourceService

from Base.base_group_views import ManagerRequiredView


class RectangleHomeView(ManagerRequiredView):
    def build_context(self):
        context = super().build_context()
        context.update(
            {
                "num_versions": SpecificationService.get_n_versions(),
                "number_of_pages": SpecificationService.get_n_pages(),
                "uploaded_sources": SourceService.get_list_of_sources(),
                "version_list": [
                    v + 1 for v in range(SpecificationService.get_n_versions())
                ],
                "page_list": [p + 1 for p in range(SpecificationService.get_n_pages())],
            }
        )
        return context

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "Rectangles/home.html", context)


class SelectRectangleView(ManagerRequiredView):
    def get(self, request: HttpRequest, version: int, page: int) -> HttpResponse:
        context = self.build_context()
        context.update({"version": version, "page_number": page})
        return render(request, "Rectangles/select.html", context)


# Create your views here.
