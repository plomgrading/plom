# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Aden Chan

from rest_framework import serializers

from .models import PedagogyTag


class PedagogyTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = PedagogyTag
        fields = "__all__"
