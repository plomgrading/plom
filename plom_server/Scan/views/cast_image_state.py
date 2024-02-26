# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechntizer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService, PaperInfoService

from Scan.services import (
    ScanCastService,
    ScanService,
    check_bundle_object_is_neither_locked_nor_pushed,
)

from plom.plom_exceptions import PlomBundleLockedException


class DiscardImageView(ScannerRequiredView):
    """Discard a particular StagingImage type."""

    def post(
        self, request: HttpRequest, *, timestamp: float, index: int
    ) -> HttpResponse:
        try:
            # TODO: Eventually bundle_id will be the arg, Issue #2621
            bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
            ScanCastService().discard_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )


class DiscardAllUnknownsView(ScannerRequiredView):
    """Discard all unknown pages from the given bundle"""

    def post(
        self, request: HttpRequest, *, timestamp: float, index: int | None
    ) -> HttpResponse:
        # note that we optionally take the index so that we can refresh the page with the correct image shown.
        try:
            # TODO: Eventually bundle_id will be the arg, Issue #2621
            bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
            ScanCastService().discard_all_unknowns_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        if index:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
            )
        else:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[bundle_id])
            )


class UnknowifyImageView(ScannerRequiredView):
    """Unknowify a particular StagingImage type."""

    def post(
        self, request: HttpRequest, *, timestamp: float, index: int
    ) -> HttpResponse:
        try:
            # TODO: Eventually bundle_id will be the arg, Issue #2621
            bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
            ScanCastService().unknowify_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )


class UnknowifyAllDiscardsView(ScannerRequiredView):
    """Unknowify all discard pages from a bundle."""

    def post(
        self, request: HttpRequest, *, timestamp: float, index: int | None
    ) -> HttpResponse:
        # note that we optionally take the index so that we can refresh the page with the correct image shown.
        try:
            # TODO: Eventually bundle_id will be the arg, Issue #2621
            bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
            ScanCastService().unknowify_all_discards_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        if index:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
            )
        else:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[bundle_id])
            )


class KnowifyImageView(ScannerRequiredView):
    """Knowify a particular StagingImage type."""

    def get(self, request, timestamp, index):
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle_from_timestamp(timestamp)

        try:
            check_bundle_object_is_neither_locked_nor_pushed(bundle)
        except PlomBundleLockedException:
            # bounce user back to scanner home page if not allowed to change things
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "slug": bundle.slug,
                "timestamp": timestamp,
                "index": index,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
            }
        )

        page_labels = [f"page {n+1}" for n in range(SpecificationService.get_n_pages())]
        all_paper_numbers = paper_info.which_papers_in_database()
        missing_papers_pages = scanner.get_bundle_missing_paper_page_numbers(bundle)
        context.update(
            {
                "page_labels": page_labels,
                "all_paper_numbers": all_paper_numbers,
                "missing_papers_pages": missing_papers_pages,
            }
        )

        return render(request, "Scan/fragments/knowify_image.html", context)

    def post(self, request, timestamp, index):
        # TODO - improve this form processing

        knowify_page_data = request.POST

        if knowify_page_data.get("bundleOrArbitrary", "off") == "on":
            try:
                paper_number, page_number = knowify_page_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Choose paper/page</div>"""
                )
        else:
            paper_number = knowify_page_data.get("arbitraryPaper", None)
            page_number = knowify_page_data.get("pageSelect", None)

        try:
            paper_number = int(paper_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Invalid paper number</div>"""
            )

        try:
            page_number = int(page_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Select a page</div>"""
            )

        # TODO: Eventually bundle_id will be the arg, Issue #2621
        bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
        try:
            ScanCastService().knowify_image_from_bundle_timestamp_and_order(
                request.user, timestamp, index, paper_number, page_number
            )
        except ValueError as err:
            return HttpResponse(f"""<div class="alert alert-danger">{err}</div>""")
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )


class ExtraliseImageView(ScannerRequiredView):
    """Extralise a particular StagingImage type."""

    def post(self, request, timestamp, index):
        # TODO - improve this form processing

        extra_page_data = request.POST

        if extra_page_data.get("bundleOrArbitrary", "off") == "on":
            paper_number = extra_page_data.get("bundlePaper", None)
        else:
            paper_number = extra_page_data.get("arbitraryPaper", None)

        try:
            paper_number = int(paper_number)
        except ValueError:
            return HttpResponse(
                """<span class="alert alert-danger">Invalid paper number</span>"""
            )

        if extra_page_data.get("questionAll", "off") == "all":
            # set all the questions
            question_list = [
                n + 1 for n in range(SpecificationService.get_n_questions())
            ]
        else:
            if len(extra_page_data.get("questions", [])):
                # NOTE - must use getlist here instead of a simple get so that return is a list
                question_list = [int(q) for q in extra_page_data.getlist("questions")]
            else:
                return HttpResponse(
                    """<span class="alert alert-danger">At least one question</span>"""
                )

        # TODO: Eventually bundle_id will be the arg, Issue #2621
        bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)

        try:
            ScanCastService().assign_extra_page_from_bundle_timestamp_and_order(
                request.user, timestamp, index, paper_number, question_list
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )

    def put(self, request, timestamp, index):
        # TODO: Eventually bundle_id will be the arg, Issue #2621
        bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
        try:
            ScanCastService().extralise_image_type_from_bundle_timestamp_and_order(
                request.user, timestamp, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )

    def delete(self, request, timestamp, index):
        # TODO: Eventually bundle_id will be the arg, Issue #2621
        bundle_id = ScanService().get_bundle_pk_from_timestamp(timestamp)
        try:
            ScanCastService().clear_extra_page_info_from_bundle_timestamp_and_order(
                request.user, timestamp, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[timestamp])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[bundle_id]) + f"?pop={index}"
        )
