# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.apps import AppConfig


class PreparationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plom_server.Preparation"
