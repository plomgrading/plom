# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.management.base import BaseCommand
from django.conf import settings

from plom.create import (
    build_extra_page_pdf,
    build_scrap_paper_pdf,
    build_bundle_separator_paper_pdf,
)

from plom_server.Base.services import Settings


class Command(BaseCommand):
    """Build the extra-page and scrap-paper PDFs and put them into static storage."""

    def handle(self, *args, **options):
        """Build and store the extra-page and scrap paper pdfs."""
        dest_dir = settings.MEDIA_ROOT / "non_db_files/"
        dest_dir.mkdir(exist_ok=True, parents=True)
        papersize = Settings.get_paper_size_latex()
        build_extra_page_pdf(dest_dir, papersize=papersize)
        build_scrap_paper_pdf(dest_dir, papersize=papersize)
        build_bundle_separator_paper_pdf(dest_dir, papersize=papersize)
