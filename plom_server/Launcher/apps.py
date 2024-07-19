# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from django.apps import AppConfig


class LaunchConfig(AppConfig):
    name = "Launcher"
    verbose_name = "A launcher app for where start-up things should go"

    # This function is called on Django startup
    def ready(self):
        print("v" * 50)
        print(
            "This app is run on django start-up, including running a management command."
        )
        print("^" * 50)
