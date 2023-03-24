# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu

from rest_framework import serializers

from Rubrics.models import RelativeRubric, NeutralRubric


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


class NeutralRubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = NeutralRubric
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
