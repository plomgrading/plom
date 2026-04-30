# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024, 2026 Colin B. Macdonald

from rest_framework import serializers

from .models import Rubric
from plom_server.QuestionTags.serializers import PedagogyTagSerializer


class RubricSerializer(serializers.ModelSerializer):
    pedagogy_tags = PedagogyTagSerializer(many=True, read_only=True, required=False)

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
