# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.apps import AppConfig


class SpecCreatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "SpecCreator"
