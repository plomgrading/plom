# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Colin B. Macdonald

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Rubric
from QuestionTags.serializers import PedagogyTagSerializer


class RubricSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    pedagogy_tags = PedagogyTagSerializer(many=True, 
                                          read_only=True, 
                                          required=False)

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
