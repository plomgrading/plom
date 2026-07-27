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

        spec = SpecificationService.get_the_spec()

        # TODO: move to demo!
        regions = QuestionRegionsService.reset_question_regions()
        QuestionRegionsService.subdivide_page(9, [23.5, 38.5], version=None)
        # Just testing
        QuestionRegionsService.set_question_regions(1, 3, [0.1, 0.2, 0.85, 0.7])

        shared_pages_info = QuestionRegionsService.get_shared_pages()

        regions = QuestionRegionsService.get_question_regions()

        # SpecificationService.get_

        pages_with_regions = sorted(list(set([r["page"] for r in regions])))
        meh = []
        for pg in pages_with_regions:
            x = {}
            x["page"] = pg
            # TODO: version hardcoded to 1
            png_bytes = ExamMockerService.get_temp_rendered_regions_page(
                x["page"], 1, regions
            )
            png_as_string = base64.b64encode(png_bytes).decode("ascii")
            x["page_region_image"] = png_as_string
            # TODO: too complicated, just get lists of questions on each page...
            for y in shared_pages_info:
                if y["page"] == pg:
                    x["question_labels_that_share_html"] = y[
                        "question_labels_that_share_html"
                    ]
            meh.append(x)

        shared_pages_info = shared_pages_info * 3

        context.update(
            {
                "allowSharedPages": spec["allowSharedPages"],
                "shared_page_info": shared_pages_info,
                "regions": regions,
                "pages_with_regions": meh,
                # "page_region_image": png_as_string,
            }
        )
        return render(request, "Preparation/question_regions.html", context)
        # except PlomDependencyConflict as err:
        #     messages.add_message(request, messages.ERROR, f"{err}")
        #     return redirect(reverse("prep_conflict"))
