# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from django.apps import AppConfig


class QuestionClusteringConfig(AppConfig):
    """Configuration for the QuestionClustering Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "plom_server.QuestionClustering"
