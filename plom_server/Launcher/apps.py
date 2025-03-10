# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.apps import AppConfig


class LauncherConfig(AppConfig):
    name = "plom_server.Launcher"
    verbose_name = "A launcher app for where start-up things should go"

    # This function is called on django startup, including
    # when a django-command is called
    def ready(self):
        """A placeholder, for now, that is called on each django start-up."""
        pass
