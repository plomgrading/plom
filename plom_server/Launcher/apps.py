# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from django.apps import AppConfig


class LaunchConfig(AppConfig):
    name = "Launcher"
    verbose_name = "A launcher app for where start-up things should go"

    # This function is called on django startup, including
    # when a django-command is called
    def ready(self):
        pass
