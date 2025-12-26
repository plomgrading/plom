# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aden Chan

from django.urls import path, re_path

from ..views import (
    MarkingProgress,
    MgetOneImage,
    MgetAllRubrics,
    MgetRubricsByQuestion,
    MgetRubricPanes,
    McreateRubric,
    MmodifyRubric,
    MlatexFragment,
    GetSolutionImage,
)


class MarkURLPatterns:
    """URLs that handle marking and interacting with plom-client.

    All of these patterns are under the route "MK,"
    e.g. "progress" will become "MK/progress"
    """

    prefix = "MK/"

    @classmethod
    def patterns(cls):
        mark_patterns = []

        # marking progress
        progress = [
            path(
                "progress/<int:question>/<int:version>",
                MarkingProgress.as_view(),
                name="api_marker_marking_progress",
            )
        ]

        mark_patterns += progress

        # Getting page-images from the server
        images = [
            path(
                "images/<int:pk>/<hash>/",
                MgetOneImage.as_view(),
                name="api_MK_one_image",
            ),
        ]
        mark_patterns += images

        # Rubric management
        rubrics = [
            path(
                "rubrics",
                MgetAllRubrics.as_view(),
                name="api_MK_get_rubric",
            ),
            re_path(
                r"rubrics/(?P<question>[0-9]{,5})$",
                MgetRubricsByQuestion.as_view(),
                name="api_MK_get_rubric",
            ),
            path(
                "user/<username>/<int:question>",
                MgetRubricPanes.as_view(),
                name="api_MK_get_rubric_panes",
            ),
            path("rubric", McreateRubric.as_view(), name="api_MK_create_rubric"),
            path(
                "rubric/<int:rid>",
                MmodifyRubric.as_view(),
                name="api_MK_modify_rubric",
            ),
        ]
        mark_patterns += rubrics

        # Get LaTeX fragments
        latex = [
            path(
                "latex",
                MlatexFragment.as_view(),
                name="api_MK_latex_fragment",
            ),
        ]
        mark_patterns += latex

        # GET: /MK/solution/{question}/{version}
        soln = [
            path(
                "solution/<int:question>/<int:version>",
                GetSolutionImage.as_view(),
                name="api_MK_solution",
            ),
        ]
        mark_patterns += soln

        return mark_patterns
