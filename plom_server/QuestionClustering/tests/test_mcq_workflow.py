# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from plom_server.QuestionClustering.models import ClusteringModelType
from plom_server.QuestionClustering.views import PreviewSelectedRectsView


class PreviewSelectedRectsViewTests(SimpleTestCase):
    """Tests for selecting the clustering model during region preview."""

    def _render_preview(self, context) -> str:
        with patch("django.urls.reverse", return_value="/"):
            return render_to_string(
                "QuestionClustering/show_rectangles.html",
                context={**context, "csrf_token": "NOTPROVIDED"},
            )

    def _get_context(self, **extra_params):
        params = {
            "question_index": 1,
            "version": 1,
            "page_num": 2,
            "left": 0.1,
            "top": 0.2,
            "right": 0.8,
            "bottom": 0.9,
            **extra_params,
        }
        request = RequestFactory().get("/preview/", data=params)
        view = PreviewSelectedRectsView()

        with (
            patch.object(view, "build_context", return_value={}),
            patch(
                "plom_server.QuestionClustering.views."
                "PaperInfoService.get_paper_numbers_containing_page",
                return_value=[],
            ),
            patch("plom_server.QuestionClustering.views.render") as mock_render,
        ):
            view.get(request)

        return mock_render.call_args.args[2]

    def test_mcq_workflow_preselects_mcq_clustering(self):
        context = self._get_context(
            question_type="MCQ",
            mcq_num_options=4,
            mcq_boxes=(
                '{"boxes": [{"label": "A", "left": 0.1, "top": 0.2, '
                '"right": 0.2, "bottom": 0.3}]}'
            ),
        )

        self.assertEqual(context["question_type"], "MCQ")
        self.assertEqual(
            context["clustering_job_form"]["choice"].value(),
            ClusteringModelType.MCQ,
        )
        html = self._render_preview(context)
        self.assertIn("Begin MCQ clustering", html)
        self.assertNotIn('id="modelSelectionModal"', html)

    def test_generic_workflow_still_requires_model_selection(self):
        context = self._get_context()

        self.assertNotIn("question_type", context)
        self.assertIsNone(context["clustering_job_form"]["choice"].value())
        html = self._render_preview(context)
        self.assertIn('id="modelSelectionModal"', html)
        self.assertIn("Single-character response (A-F, a-f)", html)
        self.assertNotIn("Multiple choice", html)
