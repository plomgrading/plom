# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import numpy as np
from typing import Any, Dict


class D3Service:
    """Service for generating D3 data."""

    def convert_stats_to_d3_hist_format(
        self, stats: dict, xlabel: str, ylabel: str, title: str
    ) -> dict:
        """Convert the question stats to a format that can be used by the histogram.

        Args:
            stats: The stats in a dict format: {label: value, ...}
            xlabel: The x-axis label.
            ylabel: The y-axis label.
            title: The title of the histogram.

        Returns:
            data in dict format that can be used by the d3 histogram.
        """
        data: Dict[str, Any] = {
            "title": title,
            "xLabel": xlabel,
            "yLabel": ylabel,
            "values": [],
        }

        for question in stats:
            data["values"].append({"label": question, "value": stats[question]})

        return data

    def convert_correlation_to_d3_heatmap_format(
        self, correlation: np.ndarray, title="", xtitle="", ytitle=""
    ) -> dict:
        """Convert the correlation matrix to a format that can be used by the heatmap.

        Args:
            correlation: The 2d correlation matrix.

        Returns:
            data in dict format that can be used by the d3 heatmap.
        """
        data = {
            "title": title,
            "rows": len(correlation),
            "cols": len(correlation[0]),
            "xTitle": xtitle,
            "yTitle": ytitle,
            "xLabel": list(range(1, len(correlation) + 1)),
            "yLabel": list(range(1, len(correlation) + 1)),
            "values": correlation.tolist(),
        }
        return data
