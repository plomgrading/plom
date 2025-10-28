# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    HttpRequest,
    HttpResponse,
    FileResponse,
    Http404,
    HttpResponseBadRequest,
)
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib import messages

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService

from ..services import SourceService


class SourceUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )


class SourceManageView(ManagerRequiredView):
    def build_context(self):
        return {
            "form": SourceUploadForm(),
            "num_versions": SpecificationService.get_n_versions(),
            "num_uploaded_source_versions": SourceService.how_many_source_versions_uploaded(),
            "number_of_pages": SpecificationService.get_n_pages(),
            "uploaded_sources": SourceService.get_list_of_sources(),
            "all_sources_uploaded": SourceService.are_all_sources_uploaded(),
            "duplicates": SourceService.check_pdf_duplication(),
        }

    def get(self, request: HttpRequest, version: int | None = None) -> HttpResponse:
        # if no spec then redirect to the dependency conflict page
        if not SpecificationService.is_there_a_spec():
            messages.add_message(
                request,
                messages.ERROR,
                "You cannot upload source pdfs until there is an assessment specification.",
            )
            return redirect(reverse("prep_conflict"))

        if version is not None:
            try:
                return FileResponse(
                    SourceService._get_source_file(version),
                    as_attachment=True,
                    filename=f"source{version}.pdf",
                )
            except ObjectDoesNotExist as e:
                raise Http404(e)

        context = self.build_context()
        return render(request, "Preparation/source_manage.html", context)

    def post(self, request, version=None):
        # This function is HTMX only
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX POST requests are allowed")

        context = {}
        if not request.FILES["source_pdf"]:
            context.update(
                {"success": False, "message": "Form invalid", "version": version}
            )
        elif version is None:
            context.update(
                {
                    "success": False,
                    "message": "Version not specified",
                    "version": version,
                }
            )
        else:
            try:
                success, message = SourceService.take_source_from_upload(
                    version,
                    request.FILES["source_pdf"],
                )
                context.update(
                    {
                        "error": not success,
                        "message": message,
                        "src": SourceService.get_source(version),
                    }
                )
            except PlomDependencyConflict as err:
                context.update(
                    {
                        "error": True,
                        "message": err,
                        "src": SourceService.get_source(version),
                    }
                )

        context.update(self.build_context())
        context.update({"request_is_htmx": request.htmx})

        return render(request, "Preparation/source_item_view.html", context)

    def delete(self, request, version):
        # This function is HTMX only
        if not request.htmx:
            return HttpResponseBadRequest("Only HTMX DELETE requests are allowed")

        try:
            SourceService.delete_source_pdf(version)
        except PlomDependencyConflict as err:
            context = {
                "error": True,
                "message": err,
                "src": SourceService.get_source(version),
            }
            return render(request, "Preparation/source_item_view.html", context)

        context = self.build_context()
        context.update(
            {
                "src": {
                    "version": version,
                    "uploaded": False,
                },
                "request_is_htmx": request.htmx,
            }
        )

        return render(request, "Preparation/source_item_view.html", context)


class ReferenceImageView(ManagerRequiredView):
    def get(self, request: HttpRequest, *, version: int, page: int) -> HttpResponse:
        return FileResponse(SourceService._get_reference_image_file(version, page))
