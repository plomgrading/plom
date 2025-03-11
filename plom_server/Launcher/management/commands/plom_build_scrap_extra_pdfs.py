# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Build the extra-page and scrap-paper PDFs and put them into static storage."""

    def handle(self, *args, **options):
        """Build and store the extra-page and scrap paper pdfs."""
        from plom.create import (
            build_extra_page_pdf,
            build_scrap_paper_pdf,
            build_bundle_separator_paper_pdf,
        )

        dest_dir = settings.STATICFILES_DIRS[0]
        build_extra_page_pdf(dest_dir)
        build_scrap_paper_pdf(dest_dir)
        build_bundle_separator_paper_pdf(dest_dir)
