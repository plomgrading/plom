# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu


from django.shortcuts import render
from django.http import Http404, FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService


# from Scan.models import StagingImage
# from Progress.services import ManageScanService

# change to valid page
# overlay for valid or discard


class ManageBundleView(ScannerRequiredView):
    """
    Let a user view an uploaded bundle and read its QR codes.
    """

    def build_context(self, timestamp, user, index):
        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, user)
        n_pages = scanner.get_n_images(bundle)
        known_pages = scanner.get_n_known_images(bundle)
        unknown_pages = scanner.get_n_unknown_images(bundle)
        extra_pages = scanner.get_n_extra_images(bundle)
        error_pages = scanner.get_n_error_images(bundle)

        if index >= n_pages:
            raise Http404("Bundle page does not exist.")

        page_info_dict = scanner.get_bundle_pages_info(bundle)
        pages = [
            page_info_dict[k] for k in range(len(page_info_dict))
        ]  # flatten into ordered list

        context.update(
            {
                "slug": bundle.slug,
                "timestamp": timestamp,
                "pages": pages,
                "current_page": pages[index],
                "index": index,
                "one_index": index + 1,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "known_pages": known_pages,
                "unknown_pages": unknown_pages,
                "extra_pages": extra_pages,
                "error_pages": error_pages,
                "finished_reading_qr": bundle.has_qr_codes,
            }
        )
        return context

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context(timestamp, request.user, index)

        return render(request, "Scan/manage_bundle.html", context)


class GetBundleNavFragmentView(ScannerRequiredView):
    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_pages = scanner.get_n_images(bundle)
        if index >= n_pages:
            raise Http404("Bundle page does not exist.")
        current_page = scanner.get_bundle_single_page_info(bundle, index)
        # page_info_dict = scanner.get_bundle_pages_info(bundle)
        # pages = [
        #     page_info_dict[k] for k in range(len(page_info_dict))
        # ]  # flatten into ordered list

        context.update(
            {
                "slug": bundle.slug,
                "timestamp": timestamp,
                "index": index,
                "one_index": index + 1,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
            }
        )

        return render(request, "Scan/fragments/nav_bundle.html", context)


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
