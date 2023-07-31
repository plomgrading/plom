# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.serializers import (
    ModelSerializer,
    StringRelatedField,
    SerializerMethodField,
    HyperlinkedRelatedField,
)

from ..models.tasks import MarkingTask


class MarkingTaskSerializer(ModelSerializer):
    assigned_user = StringRelatedField()
    status = SerializerMethodField()
    paper = StringRelatedField()
    tags = SerializerMethodField()
    latest_annotation = HyperlinkedRelatedField("annotations-detail", read_only=True)

    class Meta:
        model = MarkingTask
        exclude = ["polymorphic_ctype"]

    def get_tags(self, obj):
        return [str(tag) for tag in obj.markingtasktag_set.all()]

    def get_status(self, obj):
        return obj.StatusChoices.choices[obj.status - 1][1]
