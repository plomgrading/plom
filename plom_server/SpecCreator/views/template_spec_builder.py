# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

import pymupdf

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from plom_server.Base.base_group_views import ManagerRequiredView

from ..services import TemplateSpecBuilderService, GUISpecBuilderService


class TemplateSpecBuilderView(ManagerRequiredView):
    """Create a template test specification toml."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        # Supply some reasonable defaults for the template build form.
        context.update(
            {
                "longName": "A long name for the test",
                "shortName": "TheTest",
                "pages": 2,
                "questions": 1,
                "versions": 1,
                "score": 5,
            }
        )
        return render(request, "SpecCreator/template_spec_builder.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()

        longName = request.POST.get("longName", "A long name for my test")
        shortName = request.POST.get("shortName", "TheTest")
        try:
            pages = int(request.POST.get("pages", 2))
            questions = int(request.POST.get("questions", 1))
            versions = int(request.POST.get("versions", 1))
            score = int(request.POST.get("score", 5))
        except ValueError:
            return redirect(".")

        generated_toml = (
            TemplateSpecBuilderService()
            .build_template_toml(
                longName=longName,
                shortName=shortName,
                pages=pages,
                questions=questions,
                versions=versions,
                score=score,
            )
            .strip()
        )

        context.update(
            {
                "generated_toml": generated_toml,
                "longName": longName,
                "shortName": shortName,
                "pages": pages,
                "questions": questions,
                "versions": versions,
                "score": score,
            }
        )
        return render(request, "SpecCreator/template_spec_builder.html", context)


class GUISpecBuilderView(ManagerRequiredView):
    """Create a test specification toml via a GUI."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "SpecCreator/gui_spec_builder.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        source_pdf = request.FILES["source_pdf"]

        try:
            image_bytes_list = GUISpecBuilderService.extract_images_from_django_pdf(
                source_pdf
            )
        except pymupdf.FileDataError:
            err_msg = f"Couldn't open '{source_pdf._name}' as a .pdf file"
            messages.add_message(request, messages.ERROR, err_msg)
            return render(request, "SpecCreator/gui_spec_builder.html", context)

        image_b64_dict = {}
        for index, img in enumerate(image_bytes_list):
            image_b64 = GUISpecBuilderService.convert_png_bytes_to_base64_str(img)
            image_b64_dict.update({index + 1: image_b64})
        context.update(
            {
                "pdf_image_dict": image_b64_dict,
            }
        )
        return render(request, "SpecCreator/gui_spec_builder.html", context)
