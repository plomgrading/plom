# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from .base import ManagerReadOnlyViewSet

from plom_server.Mark.models import Annotation
from plom_server.Mark.serializers import AnnotationSerializer


class AnnotationViewSet(ManagerReadOnlyViewSet):
    """Endpoints for the Annotation model. Only safe methods are enabled.

    'annotations/':
        GET: list all annotations (can be filtered)
        POST: create a new annotation (disabled)

    'annotations/pk/':
        GET: retrieve annotation by primary key
        PUT: update annotation by primary key (disabled)
        PATCH: modify annotation by primary key (disabled)
        DELETE: delete annotation by primary key (disabled)
    """

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    filterset_fields = (
        "edition",
        "score",
        "marking_time",
        "task",
        "user",
    )
