# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024, 2025 Colin B. Macdonald

from django.apps import AppConfig


class RubricsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plom_server.Rubrics"
