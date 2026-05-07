# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024, 2026 Colin B. Macdonald

from rest_framework import serializers

from .models import MarkingTask


class MarkingTaskSerializer(serializers.ModelSerializer):
    """This class is used by Django to convert objects into dict, and maybe other things.

    Otherwise, using things like ``.values()`` converts references into integers
    via their ID.  Having a serializer allows us some control over that process.
    Currently this is only used in one place, to convert about of tasks associated
    with a rubric into a form that can be sent over the API.  Its possible it should
    be used in more places.
    """

    assigned_user = serializers.StringRelatedField()
    status = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    # careful: "paper" will be the id of the paper object, Issue #3522.
    paper_number = serializers.SerializerMethodField()

    class Meta:
        model = MarkingTask
        fields = "__all__"

    def get_tags(self, obj):
        return [str(tag) for tag in obj.markingtasktag_set.all()]

    def get_status(self, obj):
        return obj.get_status_display()

    def get_paper_number(self, obj):
        return obj.paper.paper_number
