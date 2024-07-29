# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from rest_framework.serializers import (
    ModelSerializer,
    StringRelatedField,
    SerializerMethodField,
    HyperlinkedRelatedField,
)


class MarkingTaskSerializer(ModelSerializer):
    assigned_user = StringRelatedField()
    status = SerializerMethodField()
    paper = StringRelatedField()
    tags = SerializerMethodField()
    # TODO: I don't see how this can know the external port number
    latest_annotation = HyperlinkedRelatedField("annotations-detail", read_only=True)

    def get_tags(self, obj):
        return [str(tag) for tag in obj.markingtasktag_set.all()]

    def get_status(self, obj):
        return obj.StatusChoices.choices[obj.status - 1][1]
