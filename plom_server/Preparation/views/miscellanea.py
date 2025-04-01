# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.conf import settings
from django.http import HttpRequest, HttpResponse, FileResponse
from django.shortcuts import render

from plom_server.Base.base_group_views import ManagerRequiredView


class MiscellaneaView(ManagerRequiredView):
    """View of miscellaneous files for download."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the rendered miscellanea page."""
        context = self.build_context()
        return render(request, "Preparation/miscellanea.html", context)


class MiscellaneaDownloadExtraPageView(ManagerRequiredView):
    """View for downloading the extra page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the extra page PDF file."""
        # services?  who needs 'em?  well maybe here does
        # TODO: check for command line tool and what it does
        return FileResponse(
            str((settings.MEDIA_ROOT / "non_db_files") / "extra_page.pdf")
        )


class MiscellaneaDownloadScrapPaperView(ManagerRequiredView):
    """View for downloading the scrap paper."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the scrap paper PDF file."""
        return FileResponse(
            str((settings.MEDIA_ROOT / "non_db_files") / "scrap_paper.pdf")
        )


class MiscellaneaDownloadBundleSeparatorView(ManagerRequiredView):
    """View for downloading the bundle separator."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the bundle separator PDF file."""
        return FileResponse(
            str((settings.MEDIA_ROOT / "non_db_files") / "bundle_separator_paper.pdf")
        )
