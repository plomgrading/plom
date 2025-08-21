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
        # TODO: hardcoding here not great: the first entry is the source code itself
        # please don't write there (Issue #2932).  2nd entry is relative to CWD, at least
        # we should have write permission there!
        destdir = settings.STATICFILES_DIRS[1]
        Path(destdir).mkdir(exist_ok=True)
        download_javascript_and_css_to_static(destdir)
