# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2025 Colin B. Macdonald

from typing import Any

import numpy as np


class D3Service:
    """Service for generating D3 data."""

    def convert_stats_to_d3_hist_format(
        self,
        stats: list[tuple[int, str, float]],
        *,
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
    ) -> dict:
        """Convert the question stats to a format that can be used by the histogram.

        Args:
            stats: The stats in a list format: [(qidx, qlabel, value), ...]

        Keyword Arg:
            xlabel: The x-axis label.
            ylabel: The y-axis label.
            title: The title of the histogram.

        Returns:
            data in dict format that can be used by the d3 histogram.
        """
        data: dict[str, Any] = {
            "title": title,
            "xLabel": xlabel,
            "yLabel": ylabel,
            "values": [{"label": qlabel, "value": v} for qidx, qlabel, v in stats],
        }
        return data

    def convert_correlation_to_d3_heatmap_format(
        self,
        correlation: np.ndarray,
        *,
        title: str = "",
        xtitle: str = "",
        ytitle: str = "",
        xlabels: list[str],
        ylabels: list[str],
    ) -> dict:
        """Convert the correlation matrix to a format that can be used by the heatmap.

        Args:
            correlation: The 2d correlation matrix.

        Keyword Args:
            title: string to use for title on top.
            xtitle: x axis overall label.
            ytitle: y axis  overall  label.
            xlabels: x axis tick labels
            ylabels: y axis tick labels

        Returns:
            data in dict format that can be used by the d3 heatmap.
        """
        data = {
            "title": title,
            "rows": correlation.shape[0],
            "cols": correlation.shape[1],
            "xTitle": xtitle,
            "yTitle": ytitle,
            "xLabel": xlabels,
            "yLabel": ylabels,
            "values": correlation.tolist(),
        }
        return data
