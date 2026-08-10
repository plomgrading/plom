# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Client for external MCQ checkbox crop inference."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
import logging
from typing import Any

import numpy as np
from PIL import Image
import requests

log = logging.getLogger(__name__)


class MCQCheckboxMLServiceError(RuntimeError):
    """Raised when the configured checkbox ML service cannot return predictions."""


@dataclass(frozen=True)
class MCQCheckboxCrop:
    """One already-cropped checkbox image plus local-only Plom metadata."""

    box_id: str
    label: str
    image: np.ndarray
    paper_number: int


@dataclass(frozen=True)
class MCQCheckboxPrediction:
    """One marked/empty checkbox prediction returned by the ML service."""

    box_id: str
    label: str
    marked: bool
    uncertain: bool
    confidence: float
    prob_fill: float
    fill_ratio: float
    paper_number: int | None = None


def _image_to_base64_png(image: np.ndarray) -> str:
    """Encode a NumPy image array as base64 PNG for the ML service."""
    if image.size == 0:
        raise MCQCheckboxMLServiceError("Cannot send an empty checkbox crop.")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    with BytesIO() as buffer:
        Image.fromarray(image).save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")


def _chunks(items: list[MCQCheckboxCrop], size: int) -> list[list[MCQCheckboxCrop]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _read_bool(raw: dict[str, Any], key: str, *, default: bool | None = None) -> bool:
    value = raw.get(key, default)
    if isinstance(value, bool):
        return value
    raise MCQCheckboxMLServiceError(
        f"Checkbox ML service prediction field {key!r} was not a boolean."
    )


class MCQCheckboxMLClient:
    """HTTP client for the crop-only MCQ checkbox endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str = "",
        timeout: float = 30.0,
        batch_size: int = 128,
    ) -> None:
        base_url = base_url.strip()
        if not base_url:
            raise MCQCheckboxMLServiceError("ML service URL is not configured.")
        self.predict_url = base_url.rstrip("/") + "/omr/infer"
        self.timeout = float(timeout)
        self.batch_size = int(batch_size)
        if self.batch_size < 1:
            raise MCQCheckboxMLServiceError("ML service batch size must be at least 1.")
        self.token = token.strip()

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def _predict_batch(
        self, crops: list[MCQCheckboxCrop]
    ) -> list[MCQCheckboxPrediction]:
        crop_by_id = {crop.box_id: crop for crop in crops}
        if len(crop_by_id) != len(crops):
            raise MCQCheckboxMLServiceError("Checkbox ML request ids must be unique.")

        payload = {
            "items": [
                {
                    "id": crop.box_id,
                    "image": _image_to_base64_png(crop.image),
                }
                for crop in crops
            ]
        }
        try:
            response = requests.post(
                self.predict_url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as err:
            raise MCQCheckboxMLServiceError(
                f"Could not reach checkbox ML service: {err}"
            ) from err

        if not response.ok:
            try:
                detail: Any = response.json()
            except ValueError:
                detail = response.text
            raise MCQCheckboxMLServiceError(
                f"Checkbox ML service returned HTTP {response.status_code}: {detail}"
            )

        try:
            data = response.json()
        except ValueError as err:
            raise MCQCheckboxMLServiceError(
                "Checkbox ML service returned non-JSON response."
            ) from err

        raw_predictions = data.get("predictions")
        if not isinstance(raw_predictions, list):
            raise MCQCheckboxMLServiceError(
                "Checkbox ML service response did not include predictions."
            )

        predictions = []
        for raw in raw_predictions:
            if not isinstance(raw, dict):
                raise MCQCheckboxMLServiceError(
                    "Checkbox ML service returned a malformed prediction."
                )
            try:
                box_id = str(raw["id"])
                crop = crop_by_id[box_id]
                marked = _read_bool(raw, "marked")
                uncertain = _read_bool(raw, "uncertain", default=False)
                confidence = float(raw.get("confidence", 0.0))
                prob_fill = float(raw.get("prob_fill", 0.0))
                fill_ratio = float(raw.get("fill_ratio", 0.0))
                log.info(
                    "MCQ checkbox ML prediction id=%s marked=%s uncertain=%s "
                    "confidence=%.3f prob_fill=%.3f prob_empty=%s fill_ratio=%s",
                    box_id,
                    marked,
                    uncertain,
                    confidence,
                    prob_fill,
                    raw.get("prob_empty"),
                    fill_ratio,
                )
                predictions.append(
                    MCQCheckboxPrediction(
                        box_id=box_id,
                        label=crop.label,
                        marked=marked,
                        uncertain=uncertain,
                        confidence=confidence,
                        prob_fill=prob_fill,
                        fill_ratio=fill_ratio,
                        paper_number=crop.paper_number,
                    )
                )
            except (KeyError, TypeError, ValueError) as err:
                raise MCQCheckboxMLServiceError(
                    "Checkbox ML service returned a malformed prediction."
                ) from err

        if len(predictions) != len(crops):
            raise MCQCheckboxMLServiceError(
                "Checkbox ML service returned "
                f"{len(predictions)} predictions for {len(crops)} crops."
            )
        return predictions

    def predict(self, crops: list[MCQCheckboxCrop]) -> list[MCQCheckboxPrediction]:
        """Return checkbox predictions for all submitted crops."""
        if not crops:
            return []

        predictions: list[MCQCheckboxPrediction] = []
        for chunk in _chunks(crops, self.batch_size):
            log.debug("Sending %s MCQ checkbox crops to ML service", len(chunk))
            predictions.extend(self._predict_batch(chunk))
        return predictions
