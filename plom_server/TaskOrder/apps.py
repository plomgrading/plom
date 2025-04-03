# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2025 Colin B. Macdonald

from django.apps import AppConfig


class TaskOrderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plom_server.TaskOrder"
