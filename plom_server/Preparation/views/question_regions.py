# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

import base64

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import ExamMockerService, QuestionRegionsService


class QuestionRegionsView(ManagerRequiredView):
    """Configure question regions."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        pg = 9
        version = 1

        spec = SpecificationService.get_the_spec()

        # TODO: move to demo!
        # regions = QuestionRegionsService.reset_question_regions()
        QuestionRegionsService.subdivide_page(pg, [23.5, 38.5], version=version)

        shared_pages_info = QuestionRegionsService.get_shared_pages()

        regions = QuestionRegionsService.get_question_regions()

        png_bytes = ExamMockerService.get_temp_rendered_regions_page(
            pg, version, regions
        )
        png_as_string = base64.b64encode(png_bytes).decode("ascii")

        context.update(
            {
                "allowSharedPages": spec["allowSharedPages"],
                "info": shared_pages_info,
                "regions": regions,
                "page_region_image": png_as_string,
            }
        )
        return render(request, "Preparation/question_regions.html", context)
        # except PlomDependencyConflict as err:
        #     messages.add_message(request, messages.ERROR, f"{err}")
        #     return redirect(reverse("prep_conflict"))
