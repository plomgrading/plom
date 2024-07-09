# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan

from rest_framework import serializers

from Rubrics.models import Rubric
from django.contrib.auth.models import User


class RubricSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Rubric
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
