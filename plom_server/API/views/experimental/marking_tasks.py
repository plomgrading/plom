# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from .base import ManagerReadOnlyViewSet

from plom_server.Mark.models import MarkingTask
from plom_server.Mark.serializers import MarkingTaskSerializer


class MarkingTaskViewSet(ManagerReadOnlyViewSet):
    """Endpoints for the MarkingTask model. Only safe methods are enabled.

    'marking-tasks/':
        GET: list of all marking tasks (can be filtered)
        POST: create a new marking task (disabled)

    'marking-tasks/pk/':
        GET: retrieve task by pk
        PUT: update task by pk (disabled)
        PATCH: modify task by pk (disabled)
        DELETE: delete task by pk (disabled)
    """

    queryset = MarkingTask.objects.all()
    serializer_class = MarkingTaskSerializer
    filterset_fields = (
        "assigned_user",
        "status",
        "paper",
        "code",
        "question_index",
        "question_version",
        "latest_annotation",
        "marking_priority",
    )
