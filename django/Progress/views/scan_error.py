# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Edith Coates

from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ManagerRequiredView
from Progress.views import BaseScanProgressPage
from Progress.services import ManageScanService


class ScanError(BaseScanProgressPage):
    """
    View and manage error pages.
    """

    def get(self, request):
        context = self.build_context("error_page")

        # TODO: Error page view needs redesign
        # mss = ManageScanService()
        # error_pages = mss.get_error_pages_list()
        context.update({"error_pages": 0, "n_error": 0})
        return render(request, "Progress/scan_error.html", context)


class ErrorPagesModal(ManagerRequiredView):
    """
    Display the error page, and give manager different
    types of actions to resolve the error page.
    """

    def get(self, request, test_paper, page_number, hash):
        context = self.build_context()

        context.update(
            {
                "test_paper": test_paper,
                "page_number": page_number,
                "error_hash": hash,
            }
        )

        return render(request, "Progress/fragments/scan_error_modal.html", context)


class ErrorPageImage(ManagerRequiredView):
    """
    Display the error page image.
    """

    def get(self, request, hash):
        mss = ManageScanService()
        error_image_obj = mss.get_error_image(hash)
        with open(str(error_image_obj.file_name), "rb") as f:
            test_paper = error_image_obj.paper_number
            page_number = error_image_obj.page_number
            error_img_file = (
                str(test_paper).zfill(5) + "_" + str(page_number) + "_error.png"
            )
            image_file = SimpleUploadedFile(
                error_img_file,
                f.read(),
                content_type="image/png",
            )
        return FileResponse(image_file)
