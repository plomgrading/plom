# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
from django.urls import path

from .views import (
    IDPredictionView,
    IDPredictionHXDeleteView,
    GetIDBoxRectangleView,
)

urlpatterns = [
    path(
        "id_prediction_del/<str:predictor>",
        IDPredictionHXDeleteView.as_view(),
        name="id_prediction_delete",
    ),
    path("id_predictions", IDPredictionView.as_view(), name="id_prediction_home"),
    path("id_rectangle", GetIDBoxRectangleView.as_view(), name="get_id_box_rectangle"),
]
