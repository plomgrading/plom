# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRefresh

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from ..services import QuestionRegionsService


class QuestionRegionsView(ManagerRequiredView):
    """Configure question regions."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render a page showing the current regions and various tools to change them."""
        context = self.build_context()

        try:
            allowSharedPages = SpecificationService.is_enabled_allowSharedPages()
        except ObjectDoesNotExist as e:
            raise Http404(e)

        # Just testing...
        # regions = QuestionRegionsService.reset_question_regions()
        # QuestionRegionsService.subdivide_page(9, [23.5, 38.5], version=None)
        # QuestionRegionsService.set_question_regions(1, 3, [0.1, 0.2, 0.85, 0.7])
        # QuestionRegionsService.set_question_regions(1, 5, [0.05, 0.1, 0.9, 0.88])

        regions = QuestionRegionsService.get_question_regions()
        region_info_per_page = QuestionRegionsService.get_region_info_per_page()

        context.update(
            {
                "allowSharedPages": allowSharedPages,
                "regions": regions,
                "region_info_per_page": region_info_per_page,
            }
        )
        return render(request, "Preparation/question_regions.html", context)
        # except PlomDependencyConflict as err:
        #     messages.add_message(request, messages.ERROR, f"{err}")
        #     return redirect(reverse("prep_conflict"))

    def delete(self, request: HttpRequest) -> HttpResponse:
        """Delete all regions, both set by this view or otherwise.

        Called by HTMX.
        """
        QuestionRegionsService.reset_question_regions()
        return HttpResponseClientRefresh()


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

        return HttpResponseClientRefresh()
