# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from plom_server.get_js import download_javascript_and_css_to_static


class Command(BaseCommand):
    """Download Javascript dependencies and cache them somewhere in static."""

    def handle(self, *args, **options):
        """Download Javascript dependencies and cache them somewhere in static."""
        # If a system-wide static dir is present and up to date, nothing to do.
        system_static = settings.PLOM_SYSTEM_STATIC
        if system_static and Path(system_static).exists():
            try:
                download_javascript_and_css_to_static(system_static, check_only=True)
                return
            except KeyError:
                pass
        destdir = settings.PLOM_BASE_DIR / "plom_extra_static"
        Path(destdir).mkdir(exist_ok=True)
        download_javascript_and_css_to_static(destdir)
