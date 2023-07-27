# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.viewsets import ModelViewSet
from rest_framework.authentication import BasicAuthentication

from API.permissions import IsManagerReadOnly

from Rubrics.models import Rubric
from Rubrics.serializers import RubricSerializer


class RubricViewSet(ModelViewSet):
    """Handles views for Rubrics. Only safe endpoints are enabled, because of the viewset permissions.

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
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsManagerReadOnly]
    filterset_fields = ("kind", "display_delta", "value", "out_of", "text")
    lookup_field = "key"
