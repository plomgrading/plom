# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
from django.urls import path

from .views import (
    IDPredictionView,
    IDPredictionHXDeleteView,
    IDBoxParentView,
    GetVIDBoxRectangleView,
)

urlpatterns = [
    path(
        "id_prediction_del/<str:predictor>",
        IDPredictionHXDeleteView.as_view(),
        name="id_prediction_delete",
    ),
    path("id_predictions", IDPredictionView.as_view(), name="id_prediction_home"),
    path(
        "vid_rectangle_parent",
        IDBoxParentView.as_view(),
        name="get_vid_box_parent",
    ),
    path(
        "vid_rectangle/<int:version>",
        GetVIDBoxRectangleView.as_view(),
        name="get_vid_box_rectangle",
    ),
]
