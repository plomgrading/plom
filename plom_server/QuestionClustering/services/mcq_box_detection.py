# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Detect MCQ option boxes inside a selected reference-page region."""

from typing import TYPE_CHECKING, Any

import cv2 as cv
import numpy as np

from plom_server.Rectangles.contour_detection import (
    adaptive_threshold_foreground,
    approximate_contour,
    contour_bounding_rect,
    deduplicate_boxes,
    find_sorted_contours,
    sort_boxes_reading_order,
)

if TYPE_CHECKING:
    # Needed only for static type checking; avoid importing Django models when
    # this image-processing module is loaded at runtime.
    from plom_server.Papers.models import ReferenceImage


OPTION_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _normalise_selection(rect: dict[str, float]) -> dict[str, float]:
    left = _clamp(min(rect["left"], rect["right"]), 0.0, 1.0)
    right = _clamp(max(rect["left"], rect["right"]), 0.0, 1.0)
    top = _clamp(min(rect["top"], rect["bottom"]), 0.0, 1.0)
    bottom = _clamp(max(rect["top"], rect["bottom"]), 0.0, 1.0)
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def _reference_to_absolute(
    selected_rect: dict[str, float], reference_rect: dict[str, float]
) -> dict[str, int]:
    width = reference_rect["right"] - reference_rect["left"]
    height = reference_rect["bottom"] - reference_rect["top"]
    return {
        "left": round(reference_rect["left"] + selected_rect["left"] * width),
        "top": round(reference_rect["top"] + selected_rect["top"] * height),
        "right": round(reference_rect["left"] + selected_rect["right"] * width),
        "bottom": round(reference_rect["top"] + selected_rect["bottom"] * height),
    }


def _absolute_to_reference(
    box: dict[str, int], reference_rect: dict[str, float]
) -> dict[str, float]:
    width = reference_rect["right"] - reference_rect["left"]
    height = reference_rect["bottom"] - reference_rect["top"]
    return {
        "left": (box["left"] - reference_rect["left"]) / width,
        "top": (box["top"] - reference_rect["top"]) / height,
        "right": (box["right"] - reference_rect["left"]) / width,
        "bottom": (box["bottom"] - reference_rect["top"]) / height,
    }


def _candidate_boxes(crop: np.ndarray) -> list[dict[str, Any]]:
    thresholded = adaptive_threshold_foreground(
        crop, block_size=35, c=15, blur_kernel=(3, 3), close_kernel=(2, 2)
    )
    contours = find_sorted_contours(thresholded, cv.RETR_TREE)

    crop_height, crop_width = crop.shape[:2]
    min_side = max(8, round(crop_height * 0.10))
    max_side = max(min_side + 1, round(crop_height * 0.90))

    boxes: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = contour_bounding_rect(contour)
        if w < min_side or h < min_side:
            continue
        if w > max_side or h > max_side:
            continue
        if x <= 1 or y <= 1 or x + w >= crop_width - 1 or y + h >= crop_height - 1:
            continue

        aspect = w / h
        if not 0.65 <= aspect <= 1.35:
            continue

        approx = approximate_contour(contour, 0.04)
        if approx is None:
            continue
        if not 4 <= len(approx) <= 8:
            continue

        contour_area = cv.contourArea(contour)
        rectangle_area = w * h
        if contour_area < rectangle_area * 0.35:
            continue

        squareness = 1.0 - abs(w - h) / max(w, h)
        area_fraction = min(rectangle_area / max(crop_width * crop_height, 1), 0.25)
        corner_score = 1.0 if len(approx) == 4 else 0.75
        boxes.append(
            {
                "left": x,
                "top": y,
                "right": x + w,
                "bottom": y + h,
                "score": squareness + area_fraction + corner_score,
            }
        )

    return deduplicate_boxes(boxes)


def detect_mcq_boxes_in_image(
    image: np.ndarray,
    reference_rect: dict[str, float],
    selected_rect: dict[str, float],
    num_options: int,
) -> list[dict[str, Any]]:
    """Detect option checkbox rectangles in an MCQ item region.

    Args:
        image: The full reference page image as a grayscale OpenCV array.
        reference_rect: The QR-code bounded page rectangle in absolute pixels.
        selected_rect: The user-selected MCQ item rectangle in Plom coordinates.
        num_options: Maximum number of option boxes to return.

    Returns:
        A left-to-right list of detected boxes.  Coordinates are provided in both
        Plom coordinates and absolute reference-image pixels.
    """
    selected_rect = _normalise_selection(selected_rect)
    crop_rect = _reference_to_absolute(selected_rect, reference_rect)
    image_height, image_width = image.shape[:2]
    crop_rect["left"] = round(_clamp(crop_rect["left"], 0, image_width - 1))
    crop_rect["right"] = round(_clamp(crop_rect["right"], 1, image_width))
    crop_rect["top"] = round(_clamp(crop_rect["top"], 0, image_height - 1))
    crop_rect["bottom"] = round(_clamp(crop_rect["bottom"], 1, image_height))

    if (
        crop_rect["right"] <= crop_rect["left"]
        or crop_rect["bottom"] <= crop_rect["top"]
    ):
        return []

    crop = image[
        crop_rect["top"] : crop_rect["bottom"],
        crop_rect["left"] : crop_rect["right"],
    ]
    boxes = _candidate_boxes(crop)
    boxes = sorted(boxes, key=lambda b: b["score"], reverse=True)[:num_options]
    boxes = sort_boxes_reading_order(boxes)

    detected = []
    for idx, box in enumerate(boxes):
        absolute_box = {
            "left": crop_rect["left"] + box["left"],
            "top": crop_rect["top"] + box["top"],
            "right": crop_rect["left"] + box["right"],
            "bottom": crop_rect["top"] + box["bottom"],
        }
        detected.append(
            {
                "label": OPTION_LABELS[idx],
                "absolute": absolute_box,
                "plom": _absolute_to_reference(absolute_box, reference_rect),
            }
        )
    return detected


def detect_mcq_boxes_for_reference_image(
    reference_image: "ReferenceImage",
    selected_rect: dict[str, float],
    num_options: int,
) -> list[dict[str, Any]]:
    """Detect MCQ option boxes from a stored reference image."""
    from plom_server.Rectangles.services.rectangle import (
        get_reference_rectangle_from_QR_data,
    )

    reference_image.image_file.open("rb")
    try:
        data = np.frombuffer(reference_image.image_file.read(), dtype=np.uint8)
    finally:
        reference_image.image_file.close()

    image = cv.imdecode(data, cv.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Could not decode reference image.")

    reference_rect = get_reference_rectangle_from_QR_data(reference_image.parsed_qr)
    return detect_mcq_boxes_in_image(
        image,
        reference_rect,
        selected_rect,
        max(1, min(num_options, len(OPTION_LABELS))),
    )
