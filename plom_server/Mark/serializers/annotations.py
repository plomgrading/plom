# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.serializers import (
    ModelSerializer,
    StringRelatedField,
    HyperlinkedRelatedField,
)

from ..models.annotations import Annotation


class AnnotationSerializer(ModelSerializer):
    user = StringRelatedField()
    image = StringRelatedField()
    task = HyperlinkedRelatedField("marking-tasks-detail", read_only=True)

    class Meta:
        model = Annotation
        exclude = ["annotation_data"]
