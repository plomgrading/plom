# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from django.urls import path

from ..views import (
    IDprogressCount,
    IDgetDoneTasks,
    IDgetNextTask,
    IDclaimOrSubmitTask,
    IDdirect,
    GetIDPredictions,
    GetClasslist,
)


class IdURLPatterns:
    """URLs for handling ID'ing tasks and interacting with the client.

    All of these patterns are under the route "ID", so the pattern
    "progress" will become "ID/progress"
    """

    prefix = "ID/"

    @classmethod
    def patterns(cls):
        id_patterns = []

        # Get overall ID progress
        progress = [
            path("progress", IDprogressCount.as_view(), name="api_ID_progress_count"),
        ]
        id_patterns += progress

        # ID task management
        # GET: /ID/tasks/complete
        # GET: /ID/tasks/available
        # PATCH: /ID/tasks/{papernum}
        # PUT: /ID/tasks/{papernum}
        tasks = [
            path(
                "tasks/complete", IDgetDoneTasks.as_view(), name="api_ID_get_done_tasks"
            ),
            path(
                "tasks/available", IDgetNextTask.as_view(), name="api_ID_get_next_task"
            ),
            path(
                "tasks/<paper_num>",
                IDclaimOrSubmitTask.as_view(),
                name="api_ID_claim_task",
            ),
        ]
        id_patterns += tasks

        # get, put and delete ID'er predictions
        predictions = [
            path(
                "predictions/", GetIDPredictions.as_view(), name="api_get_predictions"
            ),
            path(
                "predictions/<predictor>",
                GetIDPredictions.as_view(),
                name="api_get_predictions_from_predictor",
            ),
            path(
                "predictions/",
                GetIDPredictions.as_view(),
                name="api_put_predictions",
            ),
            path(
                "predictions/",
                GetIDPredictions.as_view(),
                name="api_delete_predictions",
            ),
            path(
                "predictions/<predictor>",
                GetIDPredictions.as_view(),
                name="api_delete_predictions_from_predictor",
            ),
        ]
        id_patterns += predictions

        # Get classlist
        classlist = [
            path("classlist/", GetClasslist.as_view(), name="api_get_classlist"),
        ]
        id_patterns += classlist

        # beta support for "direct IDing", bypassing tasks (legacy had these without "beta")
        id_patterns += [
            # /ID/beta/<papernum>/...
            path("beta/<int:papernum>", IDdirect.as_view(), name="api_ID_beta_direct"),
        ]

        return id_patterns
