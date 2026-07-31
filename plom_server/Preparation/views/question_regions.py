# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import QuestionRegionsService


class QuestionRegionsView(ManagerRequiredView):
    """Configure question regions."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()

        spec = SpecificationService.get_the_spec()

        # TODO: move to demo!
        # regions = QuestionRegionsService.reset_question_regions()
        # QuestionRegionsService.subdivide_page(9, [23.5, 38.5], version=None)
        # Just testing
        # QuestionRegionsService.set_question_regions(1, 3, [0.1, 0.2, 0.85, 0.7])

        shared_pages_info = QuestionRegionsService.get_shared_pages()

        regions = QuestionRegionsService.get_question_regions()
        region_mockups = QuestionRegionsService.get_region_mockups()

        context.update(
            {
                "allowSharedPages": spec["allowSharedPages"],
                "shared_page_info": shared_pages_info,
                "regions": regions,
                "pages_with_regions": region_mockups,
                # "page_region_image": png_as_string,
            }
        )
        return render(request, "Preparation/question_regions.html", context)
        # except PlomDependencyConflict as err:
        #     messages.add_message(request, messages.ERROR, f"{err}")
        #     return redirect(reverse("prep_conflict"))


class QuestionRegionsSubdivideView(ManagerRequiredView):
    """Post a form to subdivide a page, called by HTMX."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle the form for subdividing a page."""
        try:
            pagenum = int(request.POST.get("page_number", ""))
        except ValueError as e:
            return HttpResponseBadRequest(e)

        s = request.POST.get("comma_div_list", "")
        try:
            div = [float(x) for x in s.split(",") if x.strip()]
        except ValueError as e:
            return HttpResponseBadRequest(e)

        # TODO: support version-specific setting
        try:
            QuestionRegionsService.subdivide_page(pagenum, div)
        except ValueError as e:
            return HttpResponseBadRequest(e)
        except ObjectDoesNotExist:
            return HttpResponse("no spec", status=409)

        return HttpResponse("thanks for the info, please refresh")
