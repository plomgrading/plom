# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Client for talking to the external Plom digit-recognition service."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.conf import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PlomDigitServiceError(RuntimeError):
    """Raised when the external Plom digit service cannot complete a request."""


@dataclass(frozen=True)
class DigitCrop:
    """One prepared digit crop to send to the external digit service."""

    image_bytes: bytes
    crop_id: str
    paper_number: int
    digit_position: int


def _make_session() -> requests.Session:
    """Build a pooled session with retries for transient transport failures."""
    retry = Retry(
        total=2,
        connect=2,
        read=0,
        status=2,
        backoff_factor=0.2,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@dataclass(frozen=True)
class PlomDigitServiceClient:
    """HTTP client for synchronous external digit-recognition requests."""

    base_url: str
    token: str = ""
    timeout: float = 30.0
    _session: requests.Session = field(
        default_factory=_make_session, repr=False, compare=False
    )

    @classmethod
    def from_settings(cls) -> "PlomDigitServiceClient":
        """Build a client from Django settings."""
        return cls(
            base_url=settings.PLOM_DIGIT_SERVICE_URL,
            token=settings.PLOM_DIGIT_SERVICE_TOKEN,
            timeout=settings.PLOM_DIGIT_SERVICE_TIMEOUT,
        )

    @property
    def _headers(self) -> dict[str, str]:
        """Return authorization headers for the configured service token."""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def check_ready(self) -> None:
        """Probe ``GET /health/ready`` and raise if the service isn't usable.

        Raises:
            PlomDigitServiceError: URL unset, service unreachable, or non-2xx.
        """
        if not self.base_url:
            raise PlomDigitServiceError("PLOM_DIGIT_SERVICE_URL is not configured")
        try:
            response = self._session.get(
                f"{self.base_url}/health/ready",
                headers=self._headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            if _is_timeout_exception(exc):
                raise PlomDigitServiceError(
                    "Digit recognition service readiness check timed out after "
                    f"{self.timeout:.1f} seconds at {self.base_url}."
                ) from exc
            if _is_connection_exception(exc):
                raise PlomDigitServiceError(
                    "Digit recognition service is not reachable at "
                    f"{self.base_url}. Is the digit server running? "
                    "Start it and try again."
                ) from exc
            raise PlomDigitServiceError(
                f"Digit recognition service unreachable at {self.base_url}: {exc}"
            ) from exc
        self._raise_for_response(response)

    def predict_digit(
        self,
        image_bytes: bytes,
        *,
        crop_id: str,
        paper_number: int,
        digit_position: int,
    ) -> list[float]:
        """Submit one prepared digit crop and return 0-9-plus-blank probabilities."""
        if not self.base_url:
            raise PlomDigitServiceError("PLOM_DIGIT_SERVICE_URL is not configured")

        payload = {
            "crop_id": crop_id,
            "paper_number": paper_number,
            "digit_position": digit_position,
            "image": base64.b64encode(image_bytes).decode("ascii"),
        }
        try:
            response = self._session.post(
                f"{self.base_url}/v1/digitid/",
                headers=self._headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            if _is_timeout_exception(exc):
                raise PlomDigitServiceError(
                    "Digit recognition service timed out after "
                    f"{self.timeout:.1f} seconds while predicting crop {crop_id}."
                ) from exc
            if _is_connection_exception(exc):
                raise PlomDigitServiceError(
                    "Digit recognition service is not reachable at "
                    f"{self.base_url}. Is the digit server running? "
                    "No heatmap was saved for the current paper."
                ) from exc
            raise PlomDigitServiceError(
                f"Digit recognition service request failed for {crop_id}: {exc}"
            ) from exc
        self._raise_for_response(response)
        data = self._json_object(response)
        self._validate_prediction_metadata(
            data,
            crop_id=crop_id,
            paper_number=paper_number,
            digit_position=digit_position,
        )
        return self._probabilities_from_response(data)

    def predict_digits(
        self, crops: Iterable[DigitCrop]
    ) -> dict[tuple[int, int], list[float]]:
        """Submit prepared digit crops and return probabilities keyed by metadata."""
        if not self.base_url:
            raise PlomDigitServiceError("PLOM_DIGIT_SERVICE_URL is not configured")

        crop_list = list(crops)
        if not crop_list:
            return {}

        payload = {
            "items": [
                {
                    "crop_id": crop.crop_id,
                    "paper_number": crop.paper_number,
                    "digit_position": crop.digit_position,
                    "image": base64.b64encode(crop.image_bytes).decode("ascii"),
                }
                for crop in crop_list
            ]
        }
        try:
            response = self._session.post(
                f"{self.base_url}/v1/digitid/ndigits/",
                headers=self._headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            if _is_timeout_exception(exc):
                crop_label = "digit crop" if len(crop_list) == 1 else "digit crops"
                raise PlomDigitServiceError(
                    "Digit recognition service timed out after "
                    f"{self.timeout:.1f} seconds while predicting "
                    f"{len(crop_list)} {crop_label}. No heatmap was saved for "
                    "the current paper; already saved paper heatmaps remain available."
                ) from exc
            if _is_connection_exception(exc):
                raise PlomDigitServiceError(
                    "Digit recognition service is not reachable at "
                    f"{self.base_url}. Is the digit server running? "
                    "No heatmap was saved for the current paper; already saved "
                    "paper heatmaps remain available."
                ) from exc
            raise PlomDigitServiceError(
                f"Digit recognition service ndigits request failed: {exc}"
            ) from exc
        self._raise_for_response(response)
        data = self._json_object(response)
        predictions = data.get("predictions")
        if not isinstance(predictions, list):
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid ndigits response shape"
            )
        if len(predictions) != len(crop_list):
            raise PlomDigitServiceError(
                "Digit recognition service returned the wrong number of predictions"
            )

        expected_crop_ids = {
            (crop.paper_number, crop.digit_position): crop.crop_id for crop in crop_list
        }
        results: dict[tuple[int, int], list[float]] = {}
        for prediction in predictions:
            if not isinstance(prediction, dict):
                raise PlomDigitServiceError(
                    "Digit recognition service returned invalid prediction shape"
                )
            paper_number, digit_position = self._validate_prediction_metadata(
                prediction
            )
            key = (paper_number, digit_position)
            if key not in expected_crop_ids:
                raise PlomDigitServiceError(
                    "Digit recognition service returned unexpected prediction metadata"
                )
            self._validate_prediction_metadata(
                prediction,
                crop_id=expected_crop_ids[key],
                paper_number=paper_number,
                digit_position=digit_position,
            )
            if key in results:
                raise PlomDigitServiceError(
                    "Digit recognition service returned duplicate prediction metadata"
                )
            results[key] = self._probabilities_from_response(prediction)

        if set(results) != set(expected_crop_ids):
            raise PlomDigitServiceError(
                "Digit recognition service did not return all predictions"
            )
        return results

    @staticmethod
    def _json_object(response: requests.Response) -> dict[str, Any]:
        """Parse a response body as a JSON object."""
        try:
            data = response.json()
        except ValueError as exc:
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid JSON"
            ) from exc
        if not isinstance(data, dict):
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid response shape"
            )
        return data

    @staticmethod
    def _probabilities_from_response(data: dict[str, Any]) -> list[float]:
        """Extract and validate an 11-class probability vector from a response."""
        probabilities = data.get("probabilities")
        if not isinstance(probabilities, list) or len(probabilities) != 11:
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid probabilities"
            )
        return [float(value) for value in probabilities]

    @staticmethod
    def _validate_prediction_metadata(
        data: dict[str, Any],
        *,
        crop_id: str | None = None,
        paper_number: int | None = None,
        digit_position: int | None = None,
    ) -> tuple[int, int]:
        """Validate echoed prediction metadata and return paper/position."""
        response_crop_id = data.get("crop_id")
        response_paper_number = data.get("paper_number")
        response_digit_position = data.get("digit_position")
        if (
            not isinstance(response_crop_id, str)
            or not isinstance(response_paper_number, int)
            or not isinstance(response_digit_position, int)
        ):
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid prediction metadata"
            )
        if (
            crop_id is not None
            and paper_number is not None
            and digit_position is not None
            and (
                response_crop_id != crop_id
                or response_paper_number != paper_number
                or response_digit_position != digit_position
            )
        ):
            raise PlomDigitServiceError(
                "Digit recognition service returned unexpected prediction metadata"
            )
        return response_paper_number, response_digit_position

    @staticmethod
    def _raise_for_response(response: requests.Response) -> None:
        """Raise a PlomDigitServiceError for non-success HTTP responses."""
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text
            try:
                detail_json = response.json()
                detail = str(detail_json.get("detail", detail_json))
            except ValueError:
                pass
            raise PlomDigitServiceError(
                "Digit recognition service request failed: "
                f"{response.status_code} {detail}"
            ) from exc


def _is_timeout_exception(exc: requests.RequestException) -> bool:
    """Return whether a requests exception represents a request timeout."""
    message = str(exc).lower()
    return isinstance(exc, requests.Timeout) or "timed out" in message


def _is_connection_exception(exc: requests.RequestException) -> bool:
    """Return whether a requests exception represents a connection failure."""
    return isinstance(exc, requests.ConnectionError)
