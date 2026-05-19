# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Client for talking to the external Plom digit-recognition service."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field

from django.conf import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PlomDigitServiceError(RuntimeError):
    """Raised when the external Plom digit service cannot complete a request."""


def _make_session() -> requests.Session:
    """Build a pooled session with retries for transient transport failures."""
    retry = Retry(
        total=2,
        connect=2,
        read=2,
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
            raise PlomDigitServiceError(
                f"Digit recognition service request failed for {crop_id}: {exc}"
            ) from exc
        self._raise_for_response(response)
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
        probabilities = data.get("probabilities")
        if not isinstance(probabilities, list) or len(probabilities) != 11:
            raise PlomDigitServiceError(
                "Digit recognition service returned invalid probabilities"
            )
        return [float(value) for value in probabilities]

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
