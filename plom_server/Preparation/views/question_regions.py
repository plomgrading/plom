# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

import base64

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from plom_server.Base.services import Settings
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import ExamMockerService


class QuestionRegionsView(ManagerRequiredView):
    """Configure question regions."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        version = 1

        # png_bytes = ExamMockerService.mock_ID_page(version, 30, 42)
        # png_as_string = base64.b64encode(png_bytes).decode("ascii")

        spec = SpecificationService.get_the_spec()
        # TODO: parse which pages have multiple questions and present those to user
        print(SpecificationService.get_question_indices())
        pg = 9
        question_pages = SpecificationService.get_question_pages()
        qindices = [k for k, v in question_pages.items() if pg in v]
        print(qindices)
        print(version)
        print(pg)
        meh = SpecificationService.get_question_index_label_pairs()
        meh = [b for (a, b) in meh if a in qindices]
        info = {"page": pg, "questions_that_share": meh}
        div = [0, 23.5, 38.5, 100]
        assert len(div) == len(qindices) + 1

        # perhaps in DB someday but for now use the general key-value store
        regions = Settings.key_value_store_get_or_none("question_regions")

        if regions is None:
            # TODO: colin hates these string keys, but json...
            regions = {
                str(qidx): [] for qidx in SpecificationService.get_question_indices()
            }
        for i, qidx in enumerate(qindices):
            # TODO: or maybe append
            # TODO: someday will need to think about multiple pages per question...
            overlap = 0.02
            top = (div[i] / 100.0) - overlap
            bottom = (div[i + 1] / 100.0) + overlap
            top = max(0, top)
            bottom = min(1, bottom)
            height = bottom - top
            regions[str(qidx)] = [{"page": pg, "rect": [0, top, 1, height]}]
        Settings.key_value_store_set("question_regions", regions)

        print(info)
        print(regions)

        png_bytes = ExamMockerService.get_temp_rendered_regions_page(
            pg, version, regions
        )
        png_as_string = base64.b64encode(png_bytes).decode("ascii")

        context.update(
            {
                # "prename_config": prenaming_config,
                # "mock_id_image": png_as_string,
                "allowSharedPages": spec["allowSharedPages"],
                "info": info,
                "regions": regions,
                "page_region_image": png_as_string,
            }
        )
        return render(request, "Preparation/question_regions.html", context)
        # except PlomDependencyConflict as err:
        #     messages.add_message(request, messages.ERROR, f"{err}")
        #     return redirect(reverse("prep_conflict"))
