# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
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

from Papers.services import SpecificationService
from Base.base_group_views import ManagerRequiredView
from Rectangles.services import (
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


class GetIDBoxRectangleView(ManagerRequiredView):
    def get_id_box_context(self, region: None | dict[str, float]) -> dict:
        context = self.build_context()
        id_page_number = SpecificationService.get_id_page_number()
        context.update({"page_number": id_page_number})

        try:
            qr_info = get_reference_rectangle(1, id_page_number)
        except ValueError as err:
            raise Http404(err)
        x_coords = [X[0] for X in qr_info.values()]
        y_coords = [X[1] for X in qr_info.values()]
        rect_top_left = [min(x_coords), min(y_coords)]
        rect_bottom_right = [max(x_coords), max(y_coords)]
        context.update(
            {
                "qr_info": qr_info,
                "top_left": rect_top_left,
                "bottom_right": rect_bottom_right,
            }
        )
        rex = RectangleExtractor(1, id_page_number)
        # note that this rectangle is stated [0,1] coords relative to qr-code positions
        initial_rectangle = rex.get_largest_rectangle_contour(region)
        if initial_rectangle:
            context.update(
                {
                    "initial_rectangle": [
                        initial_rectangle["left_f"],
                        initial_rectangle["top_f"],
                        initial_rectangle["right_f"],
                        initial_rectangle["bottom_f"],
                    ]
                }
            )
        return context

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.get_id_box_context(region=None)
        return render(request, "Identify/find_id_rect.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        # get the rectangle coordinates
        left_f = round(float(request.POST.get("plom_left")), 6)
        top_f = round(float(request.POST.get("plom_top")), 6)
        right_f = round(float(request.POST.get("plom_right")), 6)
        bottom_f = round(float(request.POST.get("plom_bottom")), 6)
        # either find a rectangle within those coords or process.
        if "find_rect" in request.POST:
            context = self.get_id_box_context(
                {
                    "left_f": left_f,
                    "right_f": right_f,
                    "top_f": top_f,
                    "bottom_f": bottom_f,
                }
            )
            return render(request, "Identify/find_id_rect.html", context)
        elif "submit" in request.POST:
            try:
                IDReaderService().run_the_id_reader_in_background_via_huey(
                    request.user,
                    (left_f, top_f, right_f, bottom_f),
                    recompute_heatmap=True,
                )
                return redirect("id_prediction_home")
            except MultipleObjectsReturned:
                # this means a ID predictor task was already running, so
                # we also redirect back to the prediction home
                return redirect("id_prediction_home")
        else:
            return redirect("get_id_box_rectangle")


class GetVIDBoxRectangleView(ManagerRequiredView):
    def delete(self, request: HttpRequest, version: int) -> HttpResponse:
        clear_idbox_rectangle(version)
        return HttpResponseClientRefresh()

    def get(self, request: HttpRequest, version: int) -> HttpResponse:
        id_page_number = SpecificationService.get_id_page_number()
        try:
            qr_info = get_reference_rectangle(version, id_page_number)
        except ValueError as err:
            raise Http404(err)

        x_coords = [X[0] for X in qr_info.values()]
        y_coords = [X[1] for X in qr_info.values()]
        rect_top_left = [min(x_coords), min(y_coords)]
        rect_bottom_right = [max(x_coords), max(y_coords)]
        context = {
            "page_number": id_page_number,
            "version": version,
            "qr_info": qr_info,
            "top_left": rect_top_left,
            "bottom_right": rect_bottom_right,
        }
        rex = RectangleExtractor(version, id_page_number)
        region = get_idbox_rectangle(version)
        if region:
            context.update(
                {
                    "initial_rectangle": [
                        region["left_f"],
                        region["top_f"],
                        region["right_f"],
                        region["bottom_f"],
                    ]
                }
            )
        else:
            region = rex.get_largest_rectangle_contour(None)
            if region:
                context.update(
                    {
                        "initial_rectangle": [
                            region["left_f"],
                            region["top_f"],
                            region["right_f"],
                            region["bottom_f"],
                        ],
                        "best_guess": True,
                    }
                )
            else:
                # could not make a decent guess
                pass
        return render(request, "Identify/find_vid_rect.html", context)

    def post(self, request: HttpRequest, version: int) -> HttpResponse:
        # get the rectangle coordinates
        left_f = round(float(request.POST.get("plom_left")), 6)
        top_f = round(float(request.POST.get("plom_top")), 6)
        right_f = round(float(request.POST.get("plom_right")), 6)
        bottom_f = round(float(request.POST.get("plom_bottom")), 6)
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
            return redirect("get_vid_box_parent")
        else:
            pass
        return redirect("get_vid_box_rectangle", version)


class IDBoxParentView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        id_page_number = SpecificationService.get_id_page_number()
        tl = {}
        br = {}
        for n in range(SpecificationService.get_n_versions()):
            qr_info = get_reference_rectangle(n + 1, id_page_number)
            x_coords = [X[0] for X in qr_info.values()]
            y_coords = [X[1] for X in qr_info.values()]
            tl[n + 1] = [min(x_coords), min(y_coords)]
            br[n + 1] = [max(x_coords), max(y_coords)]

        the_idpages = [
            {
                "version": n + 1,
                "rectangle": get_idbox_rectangle(n + 1),
                "top_left": tl[n + 1],
                "bottom_right": br[n + 1],
            }
            for n in range(SpecificationService.get_n_versions())
        ]

        left_to_set = [X["version"] for X in the_idpages if X["rectangle"] is None]
        context = {
            "page_number": id_page_number,
            "idpage_list": the_idpages,
            "left_to_set": left_to_set,
        }
        return render(request, "Identify/parent_idbox_rect.html", context)
