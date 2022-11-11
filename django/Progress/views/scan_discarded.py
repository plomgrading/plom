# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.shortcuts import render
from django.http import FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView

from Progress.services import ManageScanService
from .scan_base import BaseScanProgressPage


class ScanDiscarded(BaseScanProgressPage):
    """
    View and manage discarded pages.
    """

    def get(self, request):
        context = self.build_context("discarded")
        mss = ManageScanService()
        context.update(
            {
                "discarded_pages": mss.get_discarded_pages_list(),
            }
        )
        return render(request, "Progress/scan_discarded.html", context)


class DiscardedPageImage(ManagerRequiredView):
    """
    Display the discarded page-image.
    """

    def get(self, request, discarded_hash):
        mss = ManageScanService()
        image = mss.get_discarded_image(discarded_hash)

        with open(image.file_name, "rb") as f:
            image_file = SimpleUploadedFile(
                f"{discarded_hash}.png", f.read(), content_type="image/png"
            )
        return FileResponse(image_file)


class DiscardedPageModal(ManagerRequiredView):
    """
    Display a dialog with a discarded page-image.
    """

    def get(self, request, discarded_hash):
        context = self.build_context()
        context.update(
            {
                "discarded_hash": discarded_hash,
            }
        )

        return render(
            request, "Progress/fragments/scan_view_discarded_page_modal.html", context
        )


class DeleteDiscardedPage(ManagerRequiredView):
    """
    Delete a discarded page-image.
    """

    def delete(self, request, discarded_hash):
        mss = ManageScanService()
        mss.delete_discarded_image(discarded_hash)

        return HttpResponseClientRefresh()
