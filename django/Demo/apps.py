# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.apps import AppConfig


class DemoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Demo"
