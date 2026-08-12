# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

import unittest

import cv2 as cv
import numpy as np

from plom_server.Rectangles.contour_detection import (
    adaptive_threshold_foreground,
    approximate_contour,
    canny_edges,
    deduplicate_boxes,
    find_sorted_contours,
    largest_contour_bounding_rect,
    sort_boxes_reading_order,
)


class ContourDetectionTests(unittest.TestCase):
    """Tests for shared contour helper functions."""

    def test_adaptive_threshold_finds_largest_foreground_bbox(self) -> None:
        image = np.full((80, 80), 255, dtype=np.uint8)
        cv.rectangle(image, (22, 18), (44, 54), 0, -1)

        thresholded = adaptive_threshold_foreground(
            image, block_size=15, c=2, blur_kernel=None
        )
        contours = find_sorted_contours(thresholded, cv.RETR_EXTERNAL)
        bbox = largest_contour_bounding_rect(contours)

        self.assertEqual(bbox, (22, 18, 23, 37))

    def test_canny_edges_find_quadrilateral_outline(self) -> None:
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        cv.rectangle(image, (20, 30), (80, 70), (0, 0, 0), 2)

        edges = canny_edges(image, threshold1=5, threshold2=255)
        contours = find_sorted_contours(edges, cv.RETR_EXTERNAL)
        approx = approximate_contour(contours[0], 0.02)

        self.assertIsNotNone(approx)
        assert approx is not None
        self.assertEqual(len(approx), 4)

    def test_deduplicate_boxes_prefers_highest_scored_close_box(self) -> None:
        boxes = [
            {
                "label": "low",
                "left": 10,
                "top": 10,
                "right": 30,
                "bottom": 30,
                "score": 1,
            },
            {
                "label": "high",
                "left": 11,
                "top": 11,
                "right": 31,
                "bottom": 31,
                "score": 3,
            },
            {
                "label": "far",
                "left": 60,
                "top": 10,
                "right": 80,
                "bottom": 30,
                "score": 2,
            },
        ]

        deduplicated = deduplicate_boxes(boxes)

        self.assertEqual([box["label"] for box in deduplicated], ["high", "far"])

    def test_sort_boxes_reading_order_groups_rows(self) -> None:
        boxes = [
            {"label": "B", "left": 40, "top": 10, "right": 50, "bottom": 20},
            {"label": "D", "left": 40, "top": 35, "right": 50, "bottom": 45},
            {"label": "A", "left": 10, "top": 12, "right": 20, "bottom": 22},
            {"label": "C", "left": 10, "top": 35, "right": 20, "bottom": 45},
        ]

        sorted_boxes = sort_boxes_reading_order(boxes)

        self.assertEqual([box["label"] for box in sorted_boxes], ["A", "B", "C", "D"])
