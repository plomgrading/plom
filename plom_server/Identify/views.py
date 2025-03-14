# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from django.core.exceptions import MultipleObjectsReturned
from django.http import (
    HttpRequest,
    HttpResponse,
    Http404,
)
from django.shortcuts import render, redirect
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from plom_server.Papers.services import SpecificationService, fixedpage_version_count
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Rectangles.services import (
    get_reference_qr_coords,
    get_reference_rectangle,
    get_idbox_rectangle,
    set_idbox_rectangle,
    clear_idbox_rectangle,
    RectangleExtractor,
)
from .services import IDReaderService, IDProgressService


class IDPredictionView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        # get the status of any running id reading task
        id_reader_task_status = IDReaderService().get_id_reader_background_task_status()
        context.update({"id_reader_task_status": id_reader_task_status})

        # get all predictions.
        all_predictions = IDReaderService().get_ID_predictions()
        print("#" * 50)
        print(all_predictions)
        print("#" * 50)
        id_task_info = IDProgressService().get_all_id_task_info()
        # massage it into a table
        prediction_table = {}
        for pn, dat in all_predictions.items():
            # dat is list of dict [{id, cert, predictor}]
            # rearrange this dat as multiple columns.
            prediction_table[pn] = {
                X["predictor"]: (X["student_id"], X["certainty"]) for X in dat
            }
            if pn in id_task_info:
                prediction_table[pn].update(
                    {
                        "image_pk": id_task_info[pn]["idpageimage_pk"],
                    }
                )
                # check if the paper has been identified
                if "student_id" in id_task_info[pn]:
                    prediction_table[pn].update(
                        {"identified": id_task_info[pn]["student_id"]}
                    )

        context.update({"predictions": prediction_table})

        return render(request, "Identify/id_prediction_home.html", context)


class IDPredictionHXDeleteView(ManagerRequiredView):
    # this view is accessed by hx-delete
    def delete(self, request: HttpRequest, predictor: str) -> HttpResponse:
        if predictor == "MLLAP":
            IDReaderService().delete_ID_predictions("MLLAP")
        elif predictor == "MLGreedy":
            IDReaderService().delete_ID_predictions("MLGreedy")

        return HttpResponseClientRedirect(reverse("id_prediction_home"))


class IDPredictionLaunchHXPutView(ManagerRequiredView):
    def put(self, request: HttpRequest) -> HttpResponse:
        # make sure all required rectangles set
        id_page_number = SpecificationService.get_id_page_number()
        id_version_counts = fixedpage_version_count(id_page_number)
        id_version_rectangles: dict[int, dict[str, float] | None] = {
            v: get_idbox_rectangle(v) for v in id_version_counts
        }
        try:
            IDReaderService().run_the_id_reader_in_background_via_huey(
                request.user,
                id_version_rectangles,
                recompute_heatmap=True,
            )
        except MultipleObjectsReturned:
            # this means a ID predictor task was already running, so
            # we also redirect back to the prediction home
            pass
        return HttpResponseClientRedirect(reverse("id_prediction_home"))


class GetIDBoxesRectangleView(ManagerRequiredView):
    def delete(self, request: HttpRequest, version: int) -> HttpResponse:
        clear_idbox_rectangle(version)
        return HttpResponseClientRefresh()

    def get(self, request: HttpRequest, version: int) -> HttpResponse:
        id_page_number = SpecificationService.get_id_page_number()
        try:
            qr_info = get_reference_qr_coords(version, id_page_number)
        except ValueError as err:
            raise Http404(err)

        # the plom-coord system defined by the location of the qr-codes
        ref_rect = get_reference_rectangle(version, id_page_number)
        rect_top_left = [ref_rect["left"], ref_rect["top"]]
        rect_bottom_right = [ref_rect["right"], ref_rect["bottom"]]
        context = {
            "page_number": id_page_number,
            "version": version,
            "qr_info": qr_info,
            "top_left": rect_top_left,
            "bottom_right": rect_bottom_right,
            "initial_rectangle": None,  # the selected rectangle
            "best_guess": False,
        }
        rex = RectangleExtractor(version, id_page_number)
        # have we found the idbox region before?
        region = get_idbox_rectangle(version)
        if not region:  # if not try to get the biggest contour
            region = rex.get_largest_rectangle_contour(None)
            if region:
                # we have managed to guess one
                context["best_guess"] = True
        # at this point we have a region to display or not
        if region:
            context["initial_rectangle"] = [
                region["left_f"],
                region["top_f"],
                region["right_f"],
                region["bottom_f"],
            ]
        else:
            # leave the initial rectangle context false.
            pass
        return render(request, "Identify/find_id_rect.html", context)

    def post(self, request: HttpRequest, version: int) -> HttpResponse:
        # get the rectangle coordinates
        left_f = float(request.POST.get("plom_left"))
        top_f = float(request.POST.get("plom_top"))
        right_f = float(request.POST.get("plom_right"))
        bottom_f = float(request.POST.get("plom_bottom"))
        region = {
            "left_f": left_f,
            "right_f": right_f,
            "top_f": top_f,
            "bottom_f": bottom_f,
        }
        if "find_rect" in request.POST:
            id_page_number = SpecificationService.get_id_page_number()
            rex = RectangleExtractor(version, id_page_number)
            found_rectangle = rex.get_largest_rectangle_contour(region)
            if found_rectangle:
                # we found a rectangle, so set it.
                set_idbox_rectangle(
                    version,
                    left=found_rectangle["left_f"],
                    top=found_rectangle["top_f"],
                    right=found_rectangle["right_f"],
                    bottom=found_rectangle["bottom_f"],
                )
        elif "submit" in request.POST:
            set_idbox_rectangle(
                version,
                left=region["left_f"],
                top=region["top_f"],
                right=region["right_f"],
                bottom=region["bottom_f"],
            )
            return redirect("get_id_box_parent")
        else:
            pass
        return redirect("get_id_box_rectangle", version)


class IDBoxParentView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        id_page_number = SpecificationService.get_id_page_number()
        id_version_counts = fixedpage_version_count(id_page_number)
        ref_tl = {}
        ref_br = {}
        unused_id_versions = []
        the_idpages = []
        for n in range(SpecificationService.get_n_versions()):
            if n + 1 in id_version_counts:
                ref_rect = get_reference_rectangle(n + 1, id_page_number)
                ref_tl[n + 1] = [ref_rect["left"], ref_rect["top"]]
                ref_br[n + 1] = [ref_rect["right"], ref_rect["bottom"]]
                the_idpages.append(
                    {
                        "version": n + 1,
                        "sel_rectangle": get_idbox_rectangle(n + 1),
                        "ref_top_left": ref_tl[n + 1],
                        "ref_bottom_right": ref_br[n + 1],
                    }
                )
            else:
                unused_id_versions.append(n + 1)

        left_to_set = [X["version"] for X in the_idpages if X["sel_rectangle"] is None]
        context = {
            "page_number": id_page_number,
            "idpage_list": the_idpages,
            "left_to_set": left_to_set,
            "unused_id_versions": unused_id_versions,
        }
        return render(request, "Identify/parent_idbox_rect.html", context)
