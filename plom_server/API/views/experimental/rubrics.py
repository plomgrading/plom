# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from .base import ManagerReadOnlyViewSet

from plom_server.Rubrics.models import Rubric
from plom_server.Rubrics.serializers import RubricSerializer


class RubricViewSet(ManagerReadOnlyViewSet):
    """Endpoints for the Rubric model. Only safe methods are enabled.

    'rubrics/':
        GET: list all rubrics (can be filtered)
        POST: create a new rubric (disabled)

    'rubrics/rid/':
        GET: retrieve rubric with rid
        PUT: update rubric by rid (disabled)
        PATCH: modify rubric by rid(disabled)
        DELETE: delete rubric by rid (disabled)
    """

    queryset = Rubric.objects.all()
    serializer_class = RubricSerializer
    filterset_fields = ("kind", "display_delta", "value", "out_of", "text")
    lookup_field = "rid"
