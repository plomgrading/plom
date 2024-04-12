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

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from ..services import SourceService, TestSourceService, PapersPrinted


class TestSourceUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )


class TestSourceManageView(ManagerRequiredView):
    def build_context(self):
        tss = TestSourceService()

        return {
            "form": TestSourceUploadForm(),
            "num_versions": SpecificationService.get_n_versions(),
            "number_test_sources_uploaded": tss.how_many_test_versions_uploaded(),
            "number_of_pages": SpecificationService.get_n_pages(),
            "uploaded_test_sources": tss.get_list_of_sources(),
            "all_sources_uploaded": SourceService.are_all_sources_uploaded(),
            "duplicates": tss.check_pdf_duplication(),
            "navbar_colour": "#AD9CFF",
            "user_group": "manager",
        }

    def get(self, request: HttpRequest, version: int | None = None) -> HttpResponse:
        if PapersPrinted.have_papers_been_printed():
            return redirect("prep_sources_view")

        if version:
            tss = TestSourceService()
            try:
                source_path = tss.get_source_pdf_path(version)
                return FileResponse(
                    open(source_path, "rb"),
                    as_attachment=True,
                    filename=f"source{version}.pdf",
                )
            except ObjectDoesNotExist:
                raise Http404("No such file")

        else:
            context = self.build_context()
            return render(request, "Preparation/test_source_manage.html", context)

    def post(self, request, version=None):
        if PapersPrinted.have_papers_been_printed():
            return redirect("prep_sources_view")

        context = self.build_context()
        if not request.FILES["source_pdf"]:
            context.update(
                {"success": False, "message": "Form invalid", "version": version}
            )
        else:
            success, message = SourceService.take_source_from_upload(
                version, SpecificationService.get_n_pages(), request.FILES["source_pdf"]
            )
            context.update({"version": version, "success": success, "message": message})

        return render(request, "Preparation/test_source_attempt.html", context)

    def delete(self, request, version=None):
        if PapersPrinted.have_papers_been_printed():
            return redirect("prep_sources_view")

        if version:
            SourceService.delete_source_pdf(version)
        return HttpResponseClientRedirect(reverse("prep_sources"))


class TestSourceReadOnlyView(ManagerRequiredView):
    def build_context(self):
        context = super().build_context()
        tss = TestSourceService()
        context.update(
            {
                "num_versions": SpecificationService.get_n_versions(),
                "number_test_sources_uploaded": tss.how_many_test_versions_uploaded(),
                "number_of_pages": SpecificationService.get_n_pages(),
                "uploaded_test_sources": tss.get_list_of_sources(),
                "all_sources_uploaded": SourceService.are_all_sources_uploaded(),
                "navbar_colour": "#AD9CFF",
                "user_group": "manager",
            }
        )
        return context

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "Preparation/test_paper_view.html", context)
