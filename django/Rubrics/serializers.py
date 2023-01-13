# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from rest_framework import serializers

from Rubrics.models import RelativeRubric


class RelativeRubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelativeRubric
        fields = "__all__"
        extra_kwargs = {
            "tags": {
                "required": False,
                "allow_blank": True,
            },
            "meta": {
                "required": False,
                "allow_blank": True,
            },
        }
