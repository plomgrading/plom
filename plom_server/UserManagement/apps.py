# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2023 Colin B. Macdonald

from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "UserManagement"
