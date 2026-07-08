# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from io import BytesIO

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from plom_server.Base.base_group_views import ManagerRequiredView

from ..services import TemplateSpecBuilderService, GUISpecBuilderService
from plom_server.Preparation.services.SourceService import (
    take_source_from_upload,
    delete_source_pdf,
)


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
    """Create a test specification via a GUI."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        SOURCE_VERSION = 1

        image_b64_dict = {}
        try:
            image_bytes_list = (
                GUISpecBuilderService.get_source_file_images_as_base64_str(
                    SOURCE_VERSION
                )
            )
            for index, img_b64 in enumerate(image_bytes_list):
                image_b64_dict.update({index + 1: img_b64})
        except ObjectDoesNotExist:
            pass
        context.update(
            {
                "pdf_image_dict": image_b64_dict,
            }
        )

        return render(request, "SpecCreator/gui_spec_builder.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        source_pdf = request.FILES["source_pdf"]
        SOURCE_VERSION = 1

        # make an internal copy of this file
        with source_pdf.open("rb") as fh:
            file_bytes = fh.read()
        pdf_file = File(BytesIO(file_bytes), name="random_name.pdf")

        # TODO: don't just delete the source every time
        delete_source_pdf(SOURCE_VERSION)
        take_source_from_upload(SOURCE_VERSION, pdf_file)

        image_bytes_list = GUISpecBuilderService.get_source_file_images_as_base64_str(
            SOURCE_VERSION
        )

        image_b64_dict = {}
        for index, img_b64 in enumerate(image_bytes_list):
            image_b64_dict.update({index + 1: img_b64})
        context.update(
            {
                "pdf_image_dict": image_b64_dict,
            }
        )
        return render(request, "SpecCreator/gui_spec_builder.html", context)
