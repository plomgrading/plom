# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-204 Andrew Rechnitzer

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ...services import ForgiveMissingService


class Command(BaseCommand):
    def handle(self, *args, **opt) -> None:
        ForgiveMissingService.forgive_missing_fixed_page_cmd("manager", 4, 5)
