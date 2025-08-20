# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.core.management.base import BaseCommand
from django.conf import settings

from plom_server.get_js import download_javascript_and_css_to_static


class Command(BaseCommand):
    """Build the extra-page and scrap-paper PDFs and put them into static storage."""

    def handle(self, *args, **options):
        """Build and store the extra-page and scrap paper pdfs."""
        # TODO: is this the right way to get "the" static source dir?
        destdir = settings.STATICFILES_DIRS[0]
        download_javascript_and_css_to_static(destdir)
