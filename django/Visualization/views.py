# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import json
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView


class VisualizationLandingView(ManagerRequiredView):
    """Landing page for creating visualizations with D3.js"""

    template_name = "Visualization/visualization_landing.html"

    def get(self, request):
        context = self.build_context()

        hist_data = {
            "xLabel": "X",
            "yLabel": "Y",
            "values": [
                {"label": "A", "value": 10},
                {"label": "B", "value": 20},
                {"label": "C", "value": 15},
            ],
        }
        hist_data = json.dumps(hist_data)

        hist_data_2 = {
            "xLabel": "X",
            "yLabel": "Y",
            "values": [
                {"label": "A", "value": 3},
                {"label": "B", "value": 1},
                {"label": "C", "value": 7},
                {"label": "D", "value": 5},
            ],
        }
        hist_data_2 = json.dumps(hist_data_2)

        heat_data = {
            "rows": 3,
            "cols": 3,
            "xTitle": "X",
            "yTitle": "Y",
            "xLabel": ["A", "B", "C"],
            "yLabel": ["1", "2", "3"],
            "values": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        }
        heat_data = json.dumps(heat_data)

        heat_data_2 = {
            "rows": 5,
            "cols": 4,
            "xTitle": "X",
            "yTitle": "Y",
            "xLabel": ["A", "B", "C", "D"],
            "yLabel": ["1", "2", "3", "4", "5"],
            "values": [
                [14, 16, 11, 17],
                [4, 8, 15, 9],
                [10, 12, 13, 18],
                [5, 6, 7, 19],
                [15, 7, 3, 11],
            ],
        }
        heat_data_2 = json.dumps(heat_data_2)

        context.update({"histogram_data": hist_data})
        context.update({"histogram_data_2": hist_data_2})
        context.update({"heat_map_data": heat_data})
        context.update({"heat_map_data_2": heat_data_2})
        return render(request, self.template_name, context=context)


class HistogramView(ManagerRequiredView):
    """Histogram view for D3.js"""

    template_name = "Visualization/histogram.html"

    def get(self, request):
        return render(request, self.template_name)


class HeatMapView(ManagerRequiredView):
    """Heat map view for D3.js"""

    template_name = "Visualization/heat_map.html"

    def get(self, request):
        return render(request, self.template_name)
