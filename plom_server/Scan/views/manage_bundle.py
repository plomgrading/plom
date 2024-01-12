# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import Http404, FileResponse

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService, PaperInfoService
from ..services import ScanService


class GetBundleImageView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        image = scanner.get_image(timestamp, request.user, index)

        return FileResponse(image.image_file)


class BundleThumbnailView(ScannerRequiredView):
    def build_context(self, timestamp, user):
        """Build a context for a particular page of a bundle.

        Args:
            timestamp (float): select a bundle by its timestamp.
            user (todo): which user.
        """
        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, user)
        n_pages = scanner.get_n_images(bundle)
        known_pages = scanner.get_n_known_images(bundle)
        unknown_pages = scanner.get_n_unknown_images(bundle)
        extra_pages = scanner.get_n_extra_images(bundle)
        discard_pages = scanner.get_n_discard_images(bundle)
        error_pages = scanner.get_n_error_images(bundle)

        # list of dicts of page info, in bundle order
        bundle_page_info_list = scanner.get_bundle_pages_info_list(bundle)
        # and get an ordered list of papers in the bundle and info about the pages for each paper that are in this bundle.
        bundle_papers_pages_list = scanner.get_bundle_papers_pages_list(bundle)
        # get a list of the paper-numbers in bundle that are missing pages
        bundle_incomplete_papers_list = [
            X[0] for X in scanner.get_bundle_missing_paper_page_numbers(bundle)
        ]

        context.update(
            {
                "is_pushed": bundle.pushed,
                "slug": bundle.slug,
                "timestamp": timestamp,
                "pages": bundle_page_info_list,
                "papers_pages_list": bundle_papers_pages_list,
                "incomplete_papers_list": bundle_incomplete_papers_list,
                "total_pages": n_pages,
                "known_pages": known_pages,
                "unknown_pages": unknown_pages,
                "extra_pages": extra_pages,
                "discard_pages": discard_pages,
                "error_pages": error_pages,
                "finished_reading_qr": bundle.has_qr_codes,
            }
        )
        return context

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context(timestamp, request.user)
        # to pop up the same image we were just at
        context.update({"pop": request.GET.get("pop", None)})

        return render(request, "Scan/bundle_thumbnails.html", context)


class GetBundleThumbnailView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        image = scanner.get_thumbnail_image(timestamp, request.user, index)

        return FileResponse(image.image_file)


class GetBundlePageFragmentView(ScannerRequiredView):
    """Return the image display fragment from a user-uploaded bundle."""

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "is_push_locked": bundle.is_push_locked,
                "slug": bundle.slug,
                "timestamp": timestamp,
                "index": index,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
            }
        )
        # If page is an extra page then we grab some data for the
        # set-extra-page-info form stuff
        if current_page["status"] == "extra":
            # TODO - we really need a list of question-labels: Issue #2716
            # This is a hack to be fixed vvvvvvvvvvvv
            question_labels = [
                f"Q.{n+1}" for n in range(SpecificationService.get_n_questions())
            ]
            paper_numbers = scanner.get_bundle_paper_numbers(bundle)
            all_paper_numbers = paper_info.which_papers_in_database()
            context.update(
                {
                    "question_labels": question_labels,
                    "bundle_paper_numbers": paper_numbers,
                    "all_paper_numbers": all_paper_numbers,
                }
            )

        return render(request, "Scan/fragments/bundle_page_view.html", context)


class BundleLockView(ScannerRequiredView):
    def get(self, request, timestamp):
        context = self.build_context()
        bundle = ScanService().get_bundle(timestamp, request.user)
        context.update({"slug": bundle.slug})
        return render(request, "Scan/bundle_is_locked.html", context)
