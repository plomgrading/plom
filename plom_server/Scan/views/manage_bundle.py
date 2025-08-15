# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Philip D. Loewen
# Copyright (C) 2025 Deep Shah
# Copyright (C) 2025 Aidan Murphy

from typing import Any

import pymupdf

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404, FileResponse, HttpRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils.decorators import method_decorator

from plom_server.Base.base_group_views import ScannerRequiredView
from plom_server.Papers.services import SpecificationService, PaperInfoService
from ..services import ScanService

from plom.misc_utils import format_int_list_with_runs
from datetime import datetime


class ThumbnailContainerFragmentView(ScannerRequiredView):
    """For http requests involving thumbnail container fragments."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Renders a thumbnail container for the specified page in a bundle.

        Args:
            request: an incoming http request.

        Keyword Args:
            bundle_id: which bundle.
            index: which page, by 1-based index into the bundle.

        Returns:
            An rendered thubnail fragment.
        """
        # list of dicts of page info, in bundle order
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        bundle_page_info_list = scanner.get_bundle_pages_info_list(bundle)
        # get the specific page we want.
        # TODO: a dict of bundle page dicts keyed by 'order' would be more convenient
        bundle_page = 0
        for item in bundle_page_info_list:
            # TODO: order was originally just for show, but the server is now reusing it
            if int(item["order"]) == index:
                bundle_page = item
                break

        context = {
            "pg": bundle_page,
            "bundle_id": bundle_id,
            "timestamp": datetime.now().timestamp(),
        }

        return render(
            request, "Scan/fragments/bundle_thumbnail_container.html", context
        )


class BundleThumbnailsView(ScannerRequiredView):
    """Handles the creation and perhaps some of the interaction with a page of thumbnails of a bundle."""

    def build_context(
        self,
        *,
        bundle_id: int | None = None,
    ) -> dict[str, Any]:
        """Build a context for a particular page of a bundle.

        Keyword Args:
            bundle_id: which bundle.
        """
        # TODO: not clear if superclass forbids this?
        assert bundle_id is not None, "bundle_id must be specified (?)"

        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)
        known_pages = scanner.get_n_known_images(bundle)
        unread_pages = scanner.get_n_unread_images(bundle)
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
        bundle_colliding_images = scanner.get_bundle_colliding_images(bundle)

        filter_options = [
            {"filter_code": X[0], "filter_name": X[1]}
            for X in [
                ("all", "all"),
                ("attn", "needs your attention"),
                ("known", "known pages"),
                ("extra", "extra pages"),
                ("ex_no_info", "extra pages without information"),
                ("error", "errors"),
                ("lowqr", "few qr codes read"),
                ("discard", "discarded pages"),
                ("unknown", "unknown pages"),
                ("unread", "unread pages"),
            ]
        ]

        context.update(
            {
                "is_pushed": bundle.pushed,
                "is_perfect": scanner.is_bundle_perfect(bundle.pk),
                "slug": bundle.slug,
                "bundle_id": bundle.pk,
                "timestamp": bundle.timestamp,
                "pages": bundle_page_info_list,
                "papers_pages_list": bundle_papers_pages_list,
                "incomplete_papers_list": bundle_incomplete_papers_list,
                "n_incomplete": len(bundle_incomplete_papers_list),
                "colliding_image_orders": bundle_colliding_images,
                "colliding_images_nice_format": format_int_list_with_runs(
                    bundle_colliding_images
                ),
                "n_collisions": len(bundle_colliding_images),
                "total_pages": n_pages,
                "known_pages": known_pages,
                "unread_pages": unread_pages,
                "unknown_pages": unknown_pages,
                "extra_pages": extra_pages,
                "discard_pages": discard_pages,
                "error_pages": error_pages,
                "has_page_images": bundle.has_page_images,
                "finished_reading_qr": bundle.has_qr_codes,
                "filter_options": filter_options,
            }
        )
        return context

    def get(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:
        """Get a page of thumbnails with manipulations options for a bundle.

        Args:
            request: incoming request.

        Keyword Args:
            bundle_id: which bundle.

        Returns:
            The response returns a template-rendered page.
            If there was no such bundle, return a 404 error page.
        """
        try:
            context = self.build_context(bundle_id=bundle_id)
        except ObjectDoesNotExist as e:
            raise Http404(e)

        return render(request, "Scan/bundle_thumbnails.html", context)


class BundleThumbnailsSummaryFragmentView(ScannerRequiredView):
    """Render summary information for a bundle.

    Per the name this is only a fragment of an HTML page.
    """

    def get(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:

        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)

        # an ordered list of papers in the bundle and info about the pages for each paper that are in this bundle.
        bundle_papers_pages_list = scanner.get_bundle_papers_pages_list(bundle)
        bundle_incomplete_papers_list = [
            X[0] for X in scanner.get_bundle_missing_paper_page_numbers(bundle)
        ]
        bundle_colliding_images = scanner.get_bundle_colliding_images(bundle)

        context.update(
            {
                "slug": bundle.slug,
                "n_collisions": len(bundle_colliding_images),
                "n_incomplete": len(bundle_incomplete_papers_list),
                "colliding_images_nice_format": format_int_list_with_runs(
                    bundle_colliding_images
                ),
                "total_pages": scanner.get_n_images(bundle),
                "known_pages": scanner.get_n_known_images(bundle),
                "unread_pages": scanner.get_n_unread_images(bundle),
                "unknown_pages": scanner.get_n_unknown_images(bundle),
                "extra_pages": scanner.get_n_extra_images(bundle),
                "discard_pages": scanner.get_n_discard_images(bundle),
                "error_pages": scanner.get_n_error_images(bundle),
                "papers_pages_list": bundle_papers_pages_list,
                "is_pushed": bundle.pushed,
                "is_perfect": scanner.is_bundle_perfect(bundle.pk),
                "has_page_images": bundle.has_page_images,
                "finished_reading_qr": bundle.has_qr_codes,
                "bundle": bundle,
                "bundle_id": bundle.pk,
                "incomplete_papers_list": bundle_incomplete_papers_list,
            }
        )

        return render(request, "Scan/fragments/bundle_summary.html", context)


class GetBundleThumbnailView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Get a thumbnail view for a particular position in a bundle.

        Args:
            request: incoming request.

        Keyword Args:
            bundle_id: which bundle.
            index: which index within the bundle.

        Returns:
            The response returns the file when everything was successful.
            If there was no such bundle or no such index within the
            bundle, we get a 404 error.
        """
        scanner = ScanService()
        try:
            image = scanner.get_thumbnail_image(bundle_id, index)
        except ObjectDoesNotExist as e:
            raise Http404(e)
        # note - is a thumbnail - so we don't need the baseimage here.
        return FileResponse(image.image_file)


class GetBundlePageFragmentView(ScannerRequiredView):
    """Return the image display fragment from a user-uploaded bundle."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)

        if index < 1 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        prev_paper_number = None

        for i in range(index - 1, 0, -1):
            page_info = scanner.get_bundle_single_page_info(bundle, i)
            if page_info.get("status") == "known":
                prev_paper_number = page_info.get("info", {}).get("paper_number")
                if prev_paper_number is not None:
                    break

        next_paper_number = None

        for i in range(index + 1, n_pages + 1):
            page_info = scanner.get_bundle_single_page_info(bundle, i)
            if page_info.get("status") == "known":
                next_paper_number = page_info.get("info", {}).get("paper_number")
                if next_paper_number is not None:
                    break

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "is_push_locked": bundle.is_push_locked,
                "slug": bundle.slug,
                "bundle_id": bundle.pk,
                "bundle_timestamp": bundle.timestamp,
                "index": index,
                "total_pages": n_pages,
                "current_page": current_page,
                "timestamp": datetime.now().timestamp(),
                "prev_paper_number": prev_paper_number,
                "next_paper_number": next_paper_number,
            }
        )
        # If page is an extra page then we grab some data for the
        # set-extra-page-info form stuff
        if current_page["status"] == "extra":
            question_labels_html = (
                SpecificationService.get_question_html_label_triples()
            )
            paper_numbers = scanner.get_bundle_paper_numbers(bundle)
            all_paper_numbers = paper_info.which_papers_in_database()
            context.update(
                {
                    "question_labels_html": question_labels_html,
                    "bundle_paper_numbers": paper_numbers,
                    "all_paper_numbers": all_paper_numbers,
                }
            )

        return render(request, "Scan/fragments/bundle_page_panel.html", context)


class BundleLockView(ScannerRequiredView):
    """Display an error message that a bundle is locked."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_is_locked.html", context)


class BundlePushCollisionView(ScannerRequiredView):
    """Display an error message that a collision was detected during push."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_push_collision.html", context)


class BundlePushBadErrorView(ScannerRequiredView):
    """Display an error message that something unexpected happened during push."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_push_bad_error.html", context)


class RecentStagedBundleRedirectView(ScannerRequiredView):
    """Handle a redirection, either to the newest unpushed bundle or the overall list."""

    def get(self, request: HttpResponse) -> HttpResponse:
        bundle = ScanService().get_most_recent_unpushed_bundle()
        if bundle is None:
            return redirect(reverse("scan_list_staged"))
        else:
            return redirect(reverse("scan_bundle_thumbnails", args=[bundle.pk]))


class HandwritingComparisonView(ScannerRequiredView):
    """Provide context for comparing an extra (unassigned) page with neighboring known papers.

    This view identifies the closest previous and next known paper numbers relative to the
    given extra page index, then finds the first page of each of those papers (if available).
    """

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Render the handwriting comparison view for a specific extra page within a bundle.

        This method:
        - Retrieves the current (extra) page based on its index.
        - Finds the closest known pages before and after the extra page.
        - Attempts to identify the first page of the nearest previous and next known papers.
        - Prepares context with all relevant page and paper metadata to assist in visual
        handwriting comparison during re-identification or reattachment tasks.

        Args:
            request: The incoming HTTP GET request.
            bundle_id: The ID of the bundle containing scanned pages.
            index: The page index of the extra (unidentified) page to compare.

        Returns:
            An HttpResponse rendering the 'handwriting_comparison.html' template with context
            including the extra page and its neighboring known papers (if any).
        """
        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)
        current_page = scanner.get_bundle_single_page_info(bundle, index)

        prev_paper_number = None
        nearest_prev_known_index = None

        # WARNING: Potentially inefficient DB access
        for i in range(index - 1, -1, -1):
            page_info = scanner.get_bundle_single_page_info(bundle, i)
            if page_info.get("status") == "known":
                prev_paper_number = page_info.get("info", {}).get("paper_number")
                nearest_prev_known_index = page_info.get("order")
                if prev_paper_number is not None:
                    break

        prev_paper_first_page_index = None
        if prev_paper_number is not None:
            all_bundle_pages = scanner.get_bundle_pages_info_list(bundle)
            for page in all_bundle_pages:
                page_info = page.get("info", {})
                page_paper_num = page_info.get("paper_number")
                page_num_in_paper = page_info.get("page_number")

                if page_paper_num is not None and page_num_in_paper is not None:
                    if (
                        int(page_paper_num) == int(prev_paper_number)
                        and int(page_num_in_paper) == 1
                    ):
                        prev_paper_first_page_index = page.get("order")
                        break

        if prev_paper_first_page_index is None:
            prev_paper_first_page_index = nearest_prev_known_index

        next_paper_number = None
        nearest_next_known_index = None

        for i in range(index + 1, n_pages):
            page_info = scanner.get_bundle_single_page_info(bundle, i)
            if page_info.get("status") == "known":
                next_paper_number = page_info.get("info", {}).get("paper_number")
                nearest_next_known_index = page_info.get("order")
                if next_paper_number is not None:
                    break

        next_paper_first_page_index = None
        if next_paper_number is not None:
            if "all_bundle_pages" not in locals():
                all_bundle_pages = scanner.get_bundle_pages_info_list(bundle)
            for page in all_bundle_pages:
                page_info = page.get("info", {})
                page_paper_num = page_info.get("paper_number")
                page_num_in_paper = page_info.get("page_number")

                if page_paper_num is not None and page_num_in_paper is not None:
                    if (
                        int(page_paper_num) == int(next_paper_number)
                        and int(page_num_in_paper) == 1
                    ):
                        next_paper_first_page_index = page.get("order")
                        break

        if next_paper_first_page_index is None:
            next_paper_first_page_index = nearest_next_known_index

        context.update(
            {
                "bundle_id": bundle_id,
                "extra_page_index": index,
                "prev_paper_number": prev_paper_number,
                "next_paper_number": next_paper_number,
                "prev_paper_first_page_index": prev_paper_first_page_index,
                "next_paper_first_page_index": next_paper_first_page_index,
                "current_page": current_page,
            }
        )
        return render(request, "Scan/handwriting_comparison.html", context)


# Override the default X-Frame-Options header (which is "DENY" in Django)
# to allow this view to be embedded in an <iframe> when served from the same origin.
@method_decorator(xframe_options_sameorigin, name="dispatch")
class GeneratePaperPDFView(ScannerRequiredView):
    """Generate and return a PDF version of a single paper within a bundle.

    Retrieves all scanned images associated with a specific paper number in the given
    bundle, assembles them into a PDF (one image per page), and returns the result as
    an inline HTTP response.
    """

    def get(
        self, request: HttpRequest, *, bundle_id: int, paper_number: int
    ) -> HttpResponse:
        """Generate a PDF from the scanned images of a specific paper in a bundle.

        This method:
        - Retrieves all scanned page metadata from the specified bundle.
        - Filters the pages belonging to the requested paper number.
        - Constructs a PDF with one image per page using the scanned images.
        - If an image file is missing, inserts a placeholder page with an error message.
        - Returns the PDF as an inline HTTP response for viewing or download.

        Args:
            request: The HTTP GET request.
            bundle_id: The ID of the bundle containing the scanned pages.
            paper_number: The paper number (within the bundle) to generate the PDF for.

        Returns:
            An HttpResponse containing the generated PDF, served with content type 'application/pdf'.
        """
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)

        all_pages = scanner.get_bundle_pages_info_list(bundle)
        paper_pages_info = [
            p
            for p in all_pages
            if p.get("info", {}).get("paper_number") == paper_number
        ]

        if not paper_pages_info:
            raise Http404(f"No pages found for paper {paper_number} in this bundle.")

        output_pdf = pymupdf.Document()
        for page_info in sorted(paper_pages_info, key=lambda x: x["order"]):
            try:
                img_file = scanner.get_original_image(
                    bundle_id, int(page_info["order"])
                )
                img_bytes = img_file.read()

                page = output_pdf.new_page(width=612, height=792)
                page.insert_image(page.rect, stream=img_bytes)

            except (ObjectDoesNotExist, FileNotFoundError):
                page = output_pdf.new_page()
                page.insert_text(
                    (72, 72),
                    f"Error: Image for page order {page_info['order']} not found.",
                )

        pdf_bytes = output_pdf.write()
        output_pdf.close()

        return HttpResponse(pdf_bytes, content_type="application/pdf")
