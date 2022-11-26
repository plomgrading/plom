# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.shortcuts import render
from django.http import Http404, FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Scan.models import StagingImage
from Progress.services import ManageScanService


class ManageBundleView(ScannerRequiredView):
    """
    Let a user view an uploaded bundle and read its QR codes.
    """

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        mss = ManageScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_pages = scanner.get_n_images(bundle)
        good_pages = scanner.get_n_complete_reading_tasks(bundle)
        error_pages = scanner.get_n_error_image(bundle)

        total_pages = mss.get_total_pages()
        scanned_pages = mss.get_scanned_pages()
        percent_pages_complete = scanned_pages / total_pages * 100

        total_papers = mss.get_total_test_papers()
        completed_papers = mss.get_completed_test_papers()
        percent_papers_complete = completed_papers / total_papers * 100

        if index >= n_pages:
            raise Http404("Bundle page does not exist.")

        # pages = [scanner.get_qr_code_reading_status(bundle, i) for i in range(n_pages)]
        pages = []
        for i in range(n_pages):
            page_dict = {}
            status = scanner.get_qr_code_reading_status(bundle, i)
            img = scanner.get_image(timestamp, request.user, i)
            page_dict.update(
                {
                    "status": status,
                    "pushed": img.pushed,
                }
            )
            pages.append(page_dict)

        qr_finished = scanner.is_bundle_reading_started(bundle)

        context.update(
            {
                "slug": bundle.slug,
                "timestamp": timestamp,
                "pages": pages,
                "qr_finished": qr_finished,
                "index": index,
                "one_index": index + 1,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "summary_total_pages": total_pages,
                "scanned_pages": scanned_pages,
                "percent_pages_complete": int(percent_pages_complete),
                "summary_total_papers": total_papers,
                "completed_papers": completed_papers,
                "percent_papers_complete": int(percent_papers_complete),
                "good_pages": good_pages,
                "error_pages": error_pages,
            }
        )
        return render(request, "Scan/manage_bundle.html", context)


class GetBundleImageView(ScannerRequiredView):
    """
    Return an image from a user-uploaded bundle
    """

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        image = scanner.get_image(timestamp, request.user, index)
        file_path = image.file_path
        with open(file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile(
                f"page_{index}.png",
                f.read(),
                content_type="image/png",
            )
        return FileResponse(uploaded_file)
