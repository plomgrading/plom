# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Shared helpers for OpenCV contour-based detection."""

from typing import Any

import cv2 as cv
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Return a grayscale version of an OpenCV image."""
    if len(image.shape) == 2:
        return image
    if len(image.shape) == 3 and image.shape[2] == 4:
        return cv.cvtColor(image, cv.COLOR_BGRA2GRAY)
    return cv.cvtColor(image, cv.COLOR_BGR2GRAY)


def canny_edges(
    image: np.ndarray,
    *,
    blur_kernel: tuple[int, int] = (3, 3),
    threshold1: int = 5,
    threshold2: int = 255,
) -> np.ndarray:
    """Preprocess an image with grayscale, blur, and Canny edge detection."""
    grey_image = to_grayscale(image)
    blurred_image = cv.GaussianBlur(grey_image, blur_kernel, 0)
    return cv.Canny(blurred_image, threshold1=threshold1, threshold2=threshold2)


def adaptive_threshold_foreground(
    image: np.ndarray,
    *,
    block_size: int,
    c: int,
    blur_kernel: tuple[int, int] | None = (3, 3),
    close_kernel: tuple[int, int] | None = None,
) -> np.ndarray:
    """Return a binary foreground image using adaptive thresholding."""
    grey_image = to_grayscale(image)
    if blur_kernel is not None:
        grey_image = cv.GaussianBlur(grey_image, blur_kernel, 0)
    thresholded = cv.adaptiveThreshold(
        grey_image,
        255,
        cv.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv.THRESH_BINARY_INV,
        block_size,
        c,
    )
    if close_kernel is not None:
        thresholded = cv.morphologyEx(
            thresholded,
            cv.MORPH_CLOSE,
            np.ones(close_kernel, dtype=np.uint8),
        )
    return thresholded


def find_contours(
    image: np.ndarray,
    retrieval_mode: int,
    approximation_method: int = cv.CHAIN_APPROX_SIMPLE,
) -> list[Any]:
    """Return contours from OpenCV across cv2 version return-shape differences."""
    contour_result = cv.findContours(image, retrieval_mode, approximation_method)
    if len(contour_result) == 2:
        contours, _ = contour_result
    else:
        _, contours, _ = contour_result
    return list(contours)


def find_sorted_contours(
    image: np.ndarray,
    retrieval_mode: int,
    approximation_method: int = cv.CHAIN_APPROX_SIMPLE,
) -> list[Any]:
    """Return image contours sorted largest-to-smallest by contour area."""
    contours = find_contours(image, retrieval_mode, approximation_method)
    return sorted(contours, key=cv.contourArea, reverse=True)


def approximate_contour(
    contour: Any, epsilon_ratio: float, *, closed: bool = True
) -> np.ndarray | None:
    """Approximate a contour polygon, returning None for degenerate contours."""
    perimeter = cv.arcLength(contour, closed)
    if perimeter <= 0:
        return None
    return cv.approxPolyDP(contour, epsilon_ratio * perimeter, closed)


def contour_bounding_rect(contour: Any) -> tuple[int, int, int, int]:
    """Return an OpenCV bounding rectangle for a contour."""
    return cv.boundingRect(contour)


def largest_contour_bounding_rect(
    contours: list[Any],
) -> tuple[int, int, int, int] | None:
    """Return the bounding rectangle for the largest contour, if any."""
    if not contours:
        return None
    return contour_bounding_rect(contours[0])


def deduplicate_boxes(boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove near-duplicate rectangle boxes, keeping the highest-scored candidate."""
    kept: list[dict[str, Any]] = []
    for box in sorted(boxes, key=lambda b: b["score"], reverse=True):
        center_x = (box["left"] + box["right"]) / 2
        center_y = (box["top"] + box["bottom"]) / 2
        too_close = False
        for other in kept:
            other_center_x = (other["left"] + other["right"]) / 2
            other_center_y = (other["top"] + other["bottom"]) / 2
            side = max(box["right"] - box["left"], box["bottom"] - box["top"])
            other_side = max(
                other["right"] - other["left"], other["bottom"] - other["top"]
            )
            if (
                abs(center_x - other_center_x) < max(side, other_side) * 0.55
                and abs(center_y - other_center_y) < max(side, other_side) * 0.55
            ):
                too_close = True
                break
        if not too_close:
            kept.append(box)
    return sorted(kept, key=lambda b: (b["left"], b["top"]))


def sort_boxes_reading_order(
    boxes: list[dict[str, Any]], *, min_row_threshold: float = 4
) -> list[dict[str, Any]]:
    """Sort boxes top-to-bottom, then left-to-right within each detected row."""
    if not boxes:
        return []

    heights = sorted(box["bottom"] - box["top"] for box in boxes)
    median_height = heights[len(heights) // 2]
    row_threshold = max(median_height * 0.75, min_row_threshold)
    rows: list[dict[str, Any]] = []

    for box in sorted(boxes, key=lambda b: (b["top"], b["left"])):
        center_y = (box["top"] + box["bottom"]) / 2
        row = next(
            (
                candidate
                for candidate in rows
                if abs(center_y - candidate["center_y"]) <= row_threshold
            ),
            None,
        )
        if row is None:
            row = {"center_y": center_y, "boxes": []}
            rows.append(row)

        row["boxes"].append(box)
        row["center_y"] = sum(
            (row_box["top"] + row_box["bottom"]) / 2 for row_box in row["boxes"]
        ) / len(row["boxes"])

    sorted_boxes: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: r["center_y"]):
        sorted_boxes.extend(sorted(row["boxes"], key=lambda b: b["left"]))
    return sorted_boxes
