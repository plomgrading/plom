# SPDX-Licence-Identifier: AGPL-3.0-or-later
# Copyright (c) 2023 Divy Patel

from django.urls import path

from Visualization.views import *


urlpatterns = [
    path("histogram/", HistogramView.as_view(), name="histogram"),
    path("heat_map/", HeatMapView.as_view(), name="heat_map"),
]
