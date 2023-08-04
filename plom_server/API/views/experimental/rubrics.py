# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from .base import ManagerReadOnlyViewSet

from Rubrics.models import Rubric
from Rubrics.serializers import RubricSerializer


class RubricViewSet(ManagerReadOnlyViewSet):
    """Endpoints for the Rubric model. Only safe methods are enabled.

    'rubrics/':
        GET: list all rubrics (can be filtered)
        POST: create a new rubric (disabled)

    'rubrics/key/':
        GET: retrieve rubric with key
        PUT: update rubric by key (disabled)
        PATCH: modify rubric by key (disabled)
        DELETE: delete rubric by key (disabled)
    """

    queryset = Rubric.objects.all()
    serializer_class = RubricSerializer
    filterset_fields = ("kind", "display_delta", "value", "out_of", "text")
    lookup_field = "key"
