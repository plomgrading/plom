# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
from django.urls import path

from .views import (
    IDPredictionView,
    IDPredictionHXDeleteView,
    IDPredictionLaunchHXPutView,
    IDBoxParentView,
    GetIDBoxesRectangleView,
)

urlpatterns = [
    path(
        "id_prediction_del/<str:predictor>",
        IDPredictionHXDeleteView.as_view(),
        name="id_prediction_delete",
    ),
    path("id_predictions", IDPredictionView.as_view(), name="id_prediction_home"),
    path(
        "id_predictions_launch",
        IDPredictionLaunchHXPutView.as_view(),
        name="id_prediction_launch",
    ),
    path(
        "id_rectangle_parent",
        IDBoxParentView.as_view(),
        name="get_id_box_parent",
    ),
    path(
        "id_rectangle/<int:version>",
        GetIDBoxesRectangleView.as_view(),
        name="get_id_box_rectangle",
    ),
]
