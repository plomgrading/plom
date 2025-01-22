# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService, PaperInfoService

from ..services import (
    ScanCastService,
    ScanService,
    check_bundle_object_is_neither_locked_nor_pushed,
)

from plom.plom_exceptions import PlomBundleLockedException


class DiscardImageView(ScannerRequiredView):
    """Discard a particular StagingImage type."""

    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ScanCastService().discard_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class DiscardAllUnknownsHTMXView(ScannerRequiredView):
    def post(
        self,
        request: HttpRequest,
        *,
        the_filter: str,
        bundle_id: int,
        pop_index: int | None,
    ) -> HttpResponse:
        """View that discards all unknowns from the given bundle.

        Notice that it optionally takes the index so that when the
        page is refreshed it can display the correct calling
        image-index.
        """
        try:
            ScanCastService().discard_all_unknowns_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        if pop_index is None:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            )
        else:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
                + f"?pop={pop_index}"
            )


class UnknowifyImageView(ScannerRequiredView):
    """Unknowify a particular StagingImage type."""

    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ScanCastService().unknowify_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class UnknowifyAllDiscardsHTMXView(ScannerRequiredView):
    def post(
        self,
        request: HttpRequest,
        *,
        the_filter: str,
        bundle_id: int,
        pop_index: int | None,
    ) -> HttpResponse:
        """View that casts all discards in the given bundle as unknowns.

        Notice that it optionally takes the page-index so that when the
        page is refreshed it can display the correct calling
        image-index.
        """
        try:
            ScanCastService().unknowify_all_discards_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        if pop_index is None:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            )
        else:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
                + f"?pop={pop_index}"
            )


class KnowifyImageView(ScannerRequiredView):
    """Knowify a particular StagingImage type."""

    def get(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle_from_pk(bundle_id)

        try:
            check_bundle_object_is_neither_locked_nor_pushed(bundle)
        except PlomBundleLockedException:
            # bounce user back to scanner home page if not allowed to change things
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "slug": bundle.slug,
                "bundle_id": bundle_id,
                "timestamp": bundle.timestamp,
                "index": index,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
                "the_filter": the_filter,
            }
        )

        page_labels = [
            f"page {n + 1}" for n in range(SpecificationService.get_n_pages())
        ]
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

    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
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

        try:
            ScanCastService().knowify_image_from_bundle_pk_and_order(
                request.user, bundle_id, index, paper_number, page_number
            )
        except ValueError as err:
            return HttpResponse(f"""<div class="alert alert-danger">{err}</div>""")
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )


class ExtraliseImageView(ScannerRequiredView):
    """Extralise a particular StagingImage type."""

    def post(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
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

        choice = extra_page_data.get("question_all_dnm", "")
        if choice == "choose_all":
            # set all the questions
            to_questions = SpecificationService.get_question_indices()
        elif choice == "choose_dnm":
            # TODO: or explicitly empty list or ...?
            to_questions = []
        elif choice == "choose_q":
            # caution: `get` would return just the last entry
            to_questions = [int(q) for q in extra_page_data.getlist("questions")]
            if not to_questions:
                return HttpResponse(
                    """<span class="alert alert-danger">At least one question</span>"""
                )
        else:
            return HttpResponse(
                """<span class="alert alert-danger">
                    Unexpected radio choice: this is a bug; please file an issue!
                </span>"""
            )

        try:
            ScanCastService().assign_extra_page_from_bundle_pk_and_order(
                request.user, bundle_id, index, paper_number, to_questions
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except ValueError as e:
            return HttpResponse(
                f"""<div class="alert alert-danger"><p>{e}</p><p>Try reloading this page.</p></div>"""
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )

    def put(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ScanCastService().extralise_image_type_from_bundle_pk_and_order(
                request.user, bundle_id, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )

    def delete(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ScanCastService().clear_extra_page_info_from_bundle_pk_and_order(
                request.user, bundle_id, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRedirect(
            reverse("scan_bundle_thumbnails", args=[the_filter, bundle_id])
            + f"?pop={index}"
        )
