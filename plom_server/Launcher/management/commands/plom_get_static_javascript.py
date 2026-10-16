# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from plom_server.get_js import download_javascript_and_css_to_static


class Command(BaseCommand):
    """Download Javascript dependencies and cache them somewhere in static."""

    def handle(self, *args, **options):
        """Download Javascript dependencies and cache them somewhere in static."""
        destdir = settings.PLOM_BASE_DIR / "plom_extra_static"
        Path(destdir).mkdir(exist_ok=True)
        download_javascript_and_css_to_static(destdir)
