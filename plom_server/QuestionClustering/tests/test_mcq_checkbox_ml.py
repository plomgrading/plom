# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

from unittest.mock import patch

from django.test import SimpleTestCase
import numpy as np

from plom_server.QuestionClustering.services.mcq_checkbox_ml import (
    MCQCheckboxCrop,
    MCQCheckboxMLClient,
)


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        return {
            "predictions": [
                {
                    "id": "opaque-0",
                    "marked": True,
                    "uncertain": False,
                    "confidence": 0.9,
                    "prob_fill": 0.95,
                    "fill_ratio": 0.31,
                }
            ]
        }


class MCQCheckboxMLClientTests(SimpleTestCase):
    def test_client_sends_only_opaque_id_and_image(self):
        captured = {}

        def fake_post(url, *, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeResponse()

        crop = MCQCheckboxCrop(
            box_id="opaque-0",
            label="A",
            image=np.zeros((8, 8), dtype=np.uint8),
            paper_number=17,
        )

        with patch(
            "plom_server.QuestionClustering.services.mcq_checkbox_ml.requests.post",
            fake_post,
        ):
            predictions = MCQCheckboxMLClient(
                "http://ml.example",
                token="secret",
                timeout=5,
                batch_size=128,
            ).predict([crop])

        item = captured["json"]["items"][0]
        self.assertEqual(captured["url"], "http://ml.example/omr/infer")
        self.assertEqual(set(item), {"id", "image"})
        self.assertEqual(item["id"], "opaque-0")
        self.assertEqual(captured["headers"], {"Authorization": "Bearer secret"})
        self.assertEqual(predictions[0].label, "A")
        self.assertEqual(predictions[0].paper_number, 17)
        self.assertTrue(predictions[0].marked)
