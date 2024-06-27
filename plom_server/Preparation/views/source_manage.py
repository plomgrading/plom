# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.urls import reverse
from django.shortcuts import render, redirect
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages

from plom.plom_exceptions import PlomDependencyConflict
from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from ..services import SourceService, PapersPrinted


class TestSourceUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )


class SourceManageView(ManagerRequiredView):
    def build_context(self):
        return {
            "form": TestSourceUploadForm(),
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
        if PapersPrinted.have_papers_been_printed():
            return redirect("prep_source_view")

        context = self.build_context()
        if not request.FILES["source_pdf"]:
            context.update(
                {"success": False, "message": "Form invalid", "version": version}
            )
        else:
            success, message = SourceService.take_source_from_upload(
                version, request.FILES["source_pdf"]
            )
            context.update({"version": version, "success": success, "message": message})

        return render(request, "Preparation/test_source_attempt.html", context)

    def delete(self, request, version=None):
        if version:
            try:
                SourceService.delete_source_pdf(version)
            except PlomDependencyConflict as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return HttpResponseClientRedirect(reverse("prep_conflict"))

        return HttpResponseClientRedirect(reverse("prep_sources"))


class ReferenceImageView(ManagerRequiredView):
    def get(self, request: HttpRequest, version: int, page: int) -> HttpRequest:
        return FileResponse(SourceService._get_reference_image_file(version, page))
