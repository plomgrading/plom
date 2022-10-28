# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.http import HttpResponse, Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from Papers.services import ImageBundleService, PaperCreatorService
from Scan.services import ScanService


class PushPageImage(ScannerRequiredView):
    """
    Once it's passed all of the validation checks, push a page image
    out of the "staging" database.
    """

    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        staging_image = scanner.get_image(timestamp, request.user, index)

        # get the test-paper number from the QR dictionary
        any_qr = list(staging_image.parsed_qr.values())[0]
        test_paper = int(any_qr["paper_id"])
        page_number = int(any_qr["page_num"])

        img_service = ImageBundleService()
        image = img_service.push_staged_image(staging_image, test_paper, page_number)

        paper_service = PaperCreatorService()
        paper_service.update_page_image(test_paper, page_number, image)

        return HttpResponse(
            '<p>Image pushed <i class="bi bi-check-circle text-success"></i></p>'
        )


class PushAllPageImages(ScannerRequiredView):
    """
    Push all page-images that pass the QR validation checks.
    """

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        img_service = ImageBundleService()
        paper_service = PaperCreatorService()

        bundle = scanner.get_bundle(timestamp, request.user)
        images = scanner.get_all_complete_images(bundle)

        for img in images:
            any_qr = list(img.parsed_qr.values())[0]
            test_paper = int(any_qr["paper_id"])
            page_number = int(any_qr["page_num"])
            pushed_img = img_service.push_staged_image(img, test_paper, page_number)
            paper_service.update_page_image(test_paper, page_number, pushed_img)

        return HttpResponseClientRefresh()
