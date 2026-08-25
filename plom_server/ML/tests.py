# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

"""Tests for clients of the external Plom ML service."""

import base64
from typing import Any
from unittest import TestCase
from unittest.mock import Mock

import requests

from .services.client import (
    DigitCrop,
    PlomDigitServiceClient,
    PlomDigitServiceError,
)


class PlomDigitServiceClientTests(TestCase):
    """Tests for synchronous digit-recognition HTTP requests."""

    probabilities = [0.05] * 10 + [0.5]

    @staticmethod
    def _response(payload: Any, *, status_code: int = 200) -> Any:
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = str(payload)
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @classmethod
    def _prediction(
        cls, crop_id: str, paper_number: int, digit_position: int
    ) -> dict[str, Any]:
        return {
            "crop_id": crop_id,
            "paper_number": paper_number,
            "digit_position": digit_position,
            "probabilities": cls.probabilities,
        }

    def test_predict_digit_sends_bearer_token_and_base64_image(self) -> None:
        session: Any = Mock(spec=requests.Session)
        session.post.return_value = self._response(
            self._prediction("paper17-pos3", 17, 3)
        )
        client = PlomDigitServiceClient(
            " https://ml.example/ ",
            token=" secret ",
            timeout=12.0,
            _session=session,
        )

        result = client.predict_digit(
            b"digit image",
            crop_id="paper17-pos3",
            paper_number=17,
            digit_position=3,
        )

        self.assertEqual(result, self.probabilities)
        session.post.assert_called_once_with(
            "https://ml.example/v1/digitid/",
            headers={"Authorization": "Bearer secret"},
            json={
                "crop_id": "paper17-pos3",
                "paper_number": 17,
                "digit_position": 3,
                "image": base64.b64encode(b"digit image").decode("ascii"),
            },
            timeout=12.0,
        )

    def test_predict_digits_accepts_predictions_in_any_order(self) -> None:
        session: Any = Mock(spec=requests.Session)
        session.post.return_value = self._response(
            {
                "predictions": [
                    self._prediction("paper17-pos2", 17, 2),
                    self._prediction("paper17-pos1", 17, 1),
                ]
            }
        )
        client = PlomDigitServiceClient("https://ml.example", _session=session)
        crops = [
            DigitCrop(b"one", "paper17-pos1", 17, 1),
            DigitCrop(b"two", "paper17-pos2", 17, 2),
        ]

        result = client.predict_digits(crops)

        self.assertEqual(
            result,
            {(17, 1): self.probabilities, (17, 2): self.probabilities},
        )
        request = session.post.call_args
        self.assertEqual(request.args[0], "https://ml.example/v1/digitid/ndigits/")
        self.assertEqual(
            [item["crop_id"] for item in request.kwargs["json"]["items"]],
            ["paper17-pos1", "paper17-pos2"],
        )

    def test_invalid_bearer_token_response_has_actionable_error(self) -> None:
        session: Any = Mock(spec=requests.Session)
        response = self._response(
            {
                "detail": {
                    "error": {
                        "code": "INVALID_BEARER_TOKEN",
                        "message": "Invalid bearer token.",
                    }
                }
            },
            status_code=403,
        )
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        session.post.return_value = response
        client = PlomDigitServiceClient("https://ml.example", _session=session)

        with self.assertRaisesRegex(PlomDigitServiceError, "403.*INVALID_BEARER_TOKEN"):
            client.predict_digit(
                b"image",
                crop_id="paper17-pos3",
                paper_number=17,
                digit_position=3,
            )

    def test_timeout_is_reported_as_service_error(self) -> None:
        session: Any = Mock(spec=requests.Session)
        session.post.side_effect = requests.Timeout("request timed out")
        client = PlomDigitServiceClient(
            "https://ml.example", timeout=4.0, _session=session
        )

        with self.assertRaisesRegex(
            PlomDigitServiceError, "timed out after 4.0 seconds"
        ):
            client.predict_digit(
                b"image",
                crop_id="paper17-pos3",
                paper_number=17,
                digit_position=3,
            )

    def test_malformed_probabilities_are_rejected(self) -> None:
        session: Any = Mock(spec=requests.Session)
        prediction = self._prediction("paper17-pos3", 17, 3)
        prediction["probabilities"] = [0.1] * 10
        session.post.return_value = self._response(prediction)
        client = PlomDigitServiceClient("https://ml.example", _session=session)

        with self.assertRaisesRegex(PlomDigitServiceError, "invalid probabilities"):
            client.predict_digit(
                b"image",
                crop_id="paper17-pos3",
                paper_number=17,
                digit_position=3,
            )
