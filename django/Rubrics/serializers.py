# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from rest_framework import serializers

from Rubrics.models import Rubric


class RubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rubric
