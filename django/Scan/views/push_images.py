# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.shortcuts import render
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
        img_service.push_staged_image(staging_image, test_paper, page_number)

        return HttpResponseClientRefresh()


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

        bundle = scanner.get_bundle(timestamp, request.user)
        images = scanner.get_all_complete_images(bundle)

        for img in images:
            any_qr = list(img.parsed_qr.values())[0]
            test_paper = int(any_qr["paper_id"])
            page_number = int(any_qr["page_num"])
            img_service.push_staged_image(img, test_paper, page_number)

        return HttpResponseClientRefresh()


class PagePushingUpdateView(ScannerRequiredView):
    """
    Get the status of pushing a page-image.
    """

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        img_service = ImageBundleService()

        bundle = scanner.get_bundle(timestamp, request.user)
        staging_img = scanner.get_image(timestamp, request.user, index)
        completed_images = scanner.get_all_complete_images(bundle)
        n_images = scanner.get_n_images(bundle)
        valid_pages = scanner.get_n_complete_reading_tasks(bundle)
        context = self.build_context()
        if valid_pages != n_images:
            context.update(
                {
                    "disabled": "disabled",
                }
            )

        context.update(
            {
                "timestamp": timestamp,
                "index": index,
                "status": img_service.get_image_pushing_status(staging_img),
                "error": img_service.get_image_pushing_message(staging_img),
                "image_exists": img_service.image_exists(staging_img.image_hash),
                "qr_finished": scanner.is_bundle_reading_finished(bundle),
                "qr_status": scanner.get_qr_code_reading_status(bundle, index),
                "all_pushed": scanner.all_complete_images_pushed(bundle),
                "in_progress": img_service.is_image_pushing_in_progress(
                    completed_images
                ),
            }
        )

        return render(request, "Scan/fragments/image_push_panel.html", context)
